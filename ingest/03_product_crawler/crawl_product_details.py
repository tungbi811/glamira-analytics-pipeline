from curl_cffi import requests
from bs4 import BeautifulSoup
import pymongo
import time
import random
import os
import re
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    MONGO_URI, DB_NAME,
    PRODUCT_INPUT_COLLECTION  as INPUT_COLLECTION,
    PRODUCT_OUTPUT_COLLECTION as OUTPUT_COLLECTION,
    PRODUCT_LOG_FILE          as LOG_FILE,
)

# Progressive backoff rounds — later rounds are slower with fewer workers to avoid rate limiting
ROUNDS = [
    (2.0, 4.0,  5),
    (5.0, 8.0,  3),
    (10.0, 15.0, 2),
]

BROWSER_LIST = ["chrome110", "chrome107", "chrome104", "chrome101", "chrome99"]

write_lock = Lock()

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def log_error(product_id, url, reason):
    """Log a crawl failure with product context."""
    logging.error(f"product_id={product_id} | url={url} | reason={reason}")

def make_catalog_url(product_id):
    """Build the canonical Glamira catalog URL for a product ID."""
    return f"https://www.glamira.com/catalog/product/view/id/{product_id}"

def parse_react_data(html, product_id):
    """Extract product fields from the var react_data JSON embedded in the page script."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            if script.string and "var react_data" in script.string:
                match = re.search(r"var react_data\s*=\s*(\{.*?\});", script.string, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    return {
                        "product_id":    str(data.get("product_id", product_id)),
                        "name":          data.get("name", ""),
                        "sku":           data.get("sku", ""),
                        "attribute_set": data.get("attribute_set", ""),
                        "type_id":       data.get("type_id", ""),
                        "price":         data.get("price", ""),
                        "min_price":     data.get("min_price", ""),
                        "max_price":     data.get("max_price", ""),
                        "gold_weight":   data.get("gold_weight", ""),
                        "product_type":  data.get("product_type", ""),
                        "category":      data.get("category", ""),
                        "category_name": data.get("category_name", ""),
                        "store_code":    data.get("store_code", ""),
                        "gender":        data.get("gender", ""),
                    }
    except Exception as e:
        log_error(product_id, "", f"react_data parse error: {str(e)[:100]}")
    return None

def crawl_one(args):
    """Crawl a single product, trying catalog URL first then original URL as fallback. Returns (product_id, url, parsed_data, source)."""
    product, browser_type, delay_min, delay_max = args
    product_id = product["product_id"]
    original_url = product.get("url", "")
    catalog_url = make_catalog_url(product_id)
    urls_to_try = [catalog_url, original_url] if original_url else [catalog_url]

    for url_to_try in urls_to_try:
        try:
            time.sleep(random.uniform(delay_min, delay_max))
            print(f"  → [{product_id}] trying: {url_to_try} | browser: {browser_type}")

            response = requests.get(url_to_try, impersonate=browser_type, timeout=15, verify=False)  # verify=False: some Glamira regional domains use self-signed certs

            if response.status_code == 200:
                parsed = parse_react_data(response.text, product_id)
                if parsed and parsed.get("name"):
                    source = "react_data_catalog" if url_to_try == catalog_url else "react_data_original"
                    return product_id, url_to_try, parsed, source

                soup = BeautifulSoup(response.text, "html.parser")
                h1 = soup.find("h1")
                if h1 and h1.text.strip():
                    parsed = {
                        "product_id": product_id, "name": h1.text.strip(),
                        "sku": "", "attribute_set": "", "type_id": "",
                        "price": "", "min_price": "", "max_price": "",
                        "gold_weight": "", "product_type": "",
                        "category": "", "category_name": "",
                        "store_code": "", "gender": ""
                    }
                    source = "h1_catalog" if url_to_try == catalog_url else "h1_original"
                    return product_id, url_to_try, parsed, source

                log_error(product_id, url_to_try, "200 but no data found")

            elif response.status_code == 429:
                log_error(product_id, url_to_try, "429 rate limited")
                time.sleep(30)
                continue

            elif response.status_code == 404:
                log_error(product_id, url_to_try, "404 product not found")
                if url_to_try == catalog_url and original_url:
                    continue
                return product_id, url_to_try, None, "failed_404"

            else:
                log_error(product_id, url_to_try, f"status {response.status_code}")
                if url_to_try == catalog_url and original_url:
                    continue
                return product_id, url_to_try, None, f"failed_{response.status_code}"

        except Exception as e:
            log_error(product_id, url_to_try, str(e)[:100])
            if url_to_try == catalog_url and original_url:
                continue
            return product_id, url_to_try, None, "failed_exception"

    return product_id, catalog_url, None, "failed_all"

def run_round(products, round_num, delay_min, delay_max, max_workers):
    """Crawl a list of products concurrently. Returns the list of products that failed for the next round."""
    total = len(products)
    print(f"\n{'='*70}")
    print(f"ROUND {round_num} | {total:,} products | delay: {delay_min}-{delay_max}s | workers: {max_workers}")
    print(f"{'='*70}")

    if total == 0:
        print("No products to process!")
        return []

    tasks = [(p, random.choice(BROWSER_LIST), delay_min, delay_max) for p in products]
    crawled = 0
    failed_products = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(crawl_one, task): task for task in tasks}

        for future in as_completed(futures):
            product_id, catalog_url, parsed, source = future.result()
            completed += 1

            if parsed is None:
                if source == "failed_404":
                    print(f"[{completed}/{total}] ✗ 404     | {product_id}")
                else:
                    print(f"[{completed}/{total}] ✗ FAILED  | {product_id} | {source}")
                    failed_products.append({"product_id": product_id, "url": catalog_url})
                continue

            crawled += 1
            print(f"[{completed}/{total}] ✓ CRAWLED | {product_id} | {parsed['name']} | gender: {parsed['gender']}")

            result = {
                "product_id":    product_id,
                "product_name":  parsed["name"],
                "sku":           parsed["sku"],
                "attribute_set": parsed["attribute_set"],
                "type_id":       parsed["type_id"],
                "price":         parsed["price"],
                "min_price":     parsed["min_price"],
                "max_price":     parsed["max_price"],
                "gold_weight":   parsed["gold_weight"],
                "product_type":  parsed["product_type"],
                "category":      parsed["category"],
                "category_name": parsed["category_name"],
                "store_code":    parsed["store_code"],
                "gender":        parsed["gender"],
                "catalog_url":   catalog_url,
                "source":        f"round{round_num}_{source}"
            }

            with write_lock:
                all_results.append(result)
                if len(all_results) % 100 == 0:
                    out_col.insert_many(all_results[-100:])
                    print(f"  → Saved {len(all_results)} to MongoDB")

    print(f"\nRound {round_num} done | ✓ {crawled:,} crawled | ✗ {len(failed_products):,} failed")
    return failed_products


if __name__ == "__main__":
    start_time = time.time()

    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    out_col = db[OUTPUT_COLLECTION]

    print("Loading product URLs from MongoDB...")
    all_products = list(db[INPUT_COLLECTION].find({}, {"_id": 0, "product_id": 1, "url": 1}))
    print(f"Total products: {len(all_products):,}")

    already_done = set(
        doc["product_id"] for doc in out_col.find({}, {"_id": 0, "product_id": 1})
    )
    if already_done:
        print(f"Already crawled : {len(already_done):,} — skipping")

    products = [p for p in all_products if p["product_id"] not in already_done]
    print(f"Remaining       : {len(products):,}")

    all_results = []

    for round_num, (delay_min, delay_max, max_workers) in enumerate(ROUNDS, start=1):
        products = run_round(products, round_num, delay_min, delay_max, max_workers)
        if not products:
            print(f"\n✓ All products crawled by round {round_num}!")
            break

    remainder = len(all_results) % 100
    if remainder:
        out_col.insert_many(all_results[-remainder:])

    elapsed = time.time() - start_time
    hours, rem = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(rem, 60)

    print(f"\n{'='*70}")
    print(f"FINAL RESULTS")
    print(f"  Total crawled : {len(all_results) + len(already_done):,}")
    print(f"  Still failed  : {len(products):,}")
    print(f"  Errors logged : {LOG_FILE}")
    print(f"  Total time    : {hours}h {minutes}m {seconds}s")
    print(f"{'='*70}")
    client.close()
