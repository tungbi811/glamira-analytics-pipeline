from curl_cffi import requests
from bs4 import BeautifulSoup
import pymongo
import csv
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
    PRODUCT_OUTPUT_CSV        as OUTPUT_CSV,
    PRODUCT_LOG_FILE          as LOG_FILE,
)

# Each round: (delay_min, delay_max, workers)
ROUNDS = [
    (2.0, 4.0,  5),    # Round 1 — all products
    (5.0, 8.0,  3),    # Round 2 — failed from round 1
    (10.0, 15.0, 2),   # Round 3 — failed from round 2
]
# ────────────────────────────────────────────────────

BROWSER_LIST = ["chrome110", "chrome107", "chrome104", "chrome101", "chrome99"]

write_lock = Lock()

# ── LOGGING SETUP ────────────────────────────────────
os.makedirs("data/processed", exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def log_error(product_id, url, reason):
    logging.error(f"product_id={product_id} | url={url} | reason={reason}")

def make_catalog_url(product_id):
    return f"https://www.glamira.com/catalog/product/view/id/{product_id}"

def parse_react_data(html, product_id):
    """Extract fields from var react_data up to gender"""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            if script.string and "var react_data" in script.string:
                match = re.search(
                    r"var react_data\s*=\s*(\{.*?\});",
                    script.string,
                    re.DOTALL
                )
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
    product, browser_type, delay_min, delay_max = args
    product_id = product["product_id"]
    original_url = product.get("url", "")
    catalog_url = make_catalog_url(product_id)

    urls_to_try = [catalog_url, original_url] if original_url else [catalog_url]

    for url_to_try in urls_to_try:
        try:
            sleep_time = random.uniform(delay_min, delay_max)
            print(f"  → [{product_id}] trying: {url_to_try} | browser: {browser_type} | delay: {sleep_time:.1f}s")
            time.sleep(sleep_time)

            response = requests.get(
                url_to_try,
                impersonate=browser_type,
                timeout=15,
                verify=False
            )

            if response.status_code == 200:
                parsed = parse_react_data(response.text, product_id)
                if parsed and parsed.get("name"):
                    source = "react_data_catalog" if url_to_try == catalog_url else "react_data_original"
                    return product_id, url_to_try, parsed, source

                # Fallback — try h1
                soup = BeautifulSoup(response.text, "html.parser")
                h1 = soup.find("h1")
                if h1 and h1.text.strip():
                    parsed = {
                        "product_id":    product_id,
                        "name":          h1.text.strip(),
                        "sku":           "",
                        "attribute_set": "",
                        "type_id":       "",
                        "price":         "",
                        "min_price":     "",
                        "max_price":     "",
                        "gold_weight":   "",
                        "product_type":  "",
                        "category":      "",
                        "category_name": "",
                        "store_code":    "",
                        "gender":        ""
                    }
                    source = "h1_catalog" if url_to_try == catalog_url else "h1_original"
                    return product_id, url_to_try, parsed, source

                log_error(product_id, url_to_try, "200 but no data found")

            elif response.status_code == 404:
                log_error(product_id, url_to_try, "404 product not found")
                if url_to_try == catalog_url and original_url:
                    print(f"  → [{product_id}] catalog 404 — trying original URL...")
                    continue
                else:
                    return product_id, url_to_try, None, "failed_404"

            elif response.status_code == 403:
                log_error(product_id, url_to_try, "403 blocked")
                if url_to_try == catalog_url and original_url:
                    print(f"  → [{product_id}] catalog 403 — trying original URL...")
                    continue
                else:
                    return product_id, url_to_try, None, "failed_403"

            elif response.status_code == 429:
                log_error(product_id, url_to_try, "429 rate limited")
                time.sleep(30)
                continue

            else:
                log_error(product_id, url_to_try, f"status {response.status_code}")
                if url_to_try == catalog_url and original_url:
                    print(f"  → [{product_id}] catalog {response.status_code} — trying original URL...")
                    continue
                else:
                    return product_id, url_to_try, None, f"failed_{response.status_code}"

        except Exception as e:
            log_error(product_id, url_to_try, str(e)[:100])
            if url_to_try == catalog_url and original_url:
                print(f"  → [{product_id}] catalog error — trying original URL...")
                continue
            else:
                return product_id, url_to_try, None, "failed_exception"

    return product_id, catalog_url, None, "failed_all"

def run_round(products, round_num, delay_min, delay_max, max_workers):
    total = len(products)
    print(f"\n{'='*70}")
    print(f"ROUND {round_num} | {total:,} products | delay: {delay_min}-{delay_max}s | workers: {max_workers}")
    print(f"{'='*70}")

    if total == 0:
        print("No products to process!")
        return []

    # Assign browser to each product
    tasks = []
    for product in products:
        browser_type = random.choice(BROWSER_LIST)
        tasks.append((product, browser_type, delay_min, delay_max))

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
                    failed_products.append({
                        "product_id": product_id,
                        "url": catalog_url
                    })
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
                writer.writerow(result)
                csvfile.flush()

                if len(all_results) % 100 == 0:
                    out_col.insert_many(all_results[-100:])
                    print(f"  → Saved {len(all_results)} to MongoDB")

    print(f"\nRound {round_num} done | ✓ {crawled:,} crawled | ✗ {len(failed_products):,} failed")
    return failed_products


# ── MAIN ────────────────────────────────────────────
start_time = time.time()

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
out_col = db[OUTPUT_COLLECTION]

print("Loading product URLs from MongoDB...")
all_products = list(db[INPUT_COLLECTION].find({}, {"_id": 0, "product_id": 1, "url": 1}))
print(f"Total products: {len(all_products):,}")

# Skip already crawled
already_done = set()
if os.path.exists(OUTPUT_CSV) and os.path.getsize(OUTPUT_CSV) > 0:
    with open(OUTPUT_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            already_done.add(row["product_id"])
    print(f"Already crawled : {len(already_done):,} — skipping")

products = [p for p in all_products if p["product_id"] not in already_done]
print(f"Remaining       : {len(products):,}")

# Fresh start or continue
if not already_done:
    out_col.drop()
    print("Fresh start — collection dropped")
else:
    print("Continuing — keeping existing MongoDB data")

all_results = []
write_header = not os.path.exists(OUTPUT_CSV) or os.path.getsize(OUTPUT_CSV) == 0

CSV_FIELDS = [
    "product_id", "product_name", "sku", "attribute_set", "type_id",
    "price", "min_price", "max_price", "gold_weight",
    "product_type", "category", "category_name",
    "store_code", "gender", "catalog_url", "source"
]

with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
    if write_header:
        writer.writeheader()

    for round_num, (delay_min, delay_max, max_workers) in enumerate(ROUNDS, start=1):
        failed_products = run_round(
            products, round_num, delay_min, delay_max, max_workers
        )
        products = failed_products

        if not products:
            print(f"\n✓ All products crawled by round {round_num}!")
            break

    # Save remaining to MongoDB
    remainder = len(all_results) % 100
    if remainder:
        out_col.insert_many(all_results[-remainder:])

# Total time
elapsed = time.time() - start_time
hours = int(elapsed // 3600)
minutes = int((elapsed % 3600) // 60)
seconds = int(elapsed % 60)

print(f"\n{'='*70}")
print(f"FINAL RESULTS")
print(f"  Total crawled : {len(all_results) + len(already_done):,}")
print(f"  Still failed  : {len(products):,}")
print(f"  Saved to      : {OUTPUT_CSV}")
print(f"  Errors logged : {LOG_FILE}")
print(f"  Total time    : {hours}h {minutes}m {seconds}s")
print(f"{'='*70}")
client.close()

