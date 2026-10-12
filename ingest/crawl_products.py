"""Crawl product details from glamira.com for every product seen in the events.

1. Builds `product_ids` (unique ids from 7 product events) once, with $out.
2. Fetches each product from the JSON endpoint the product page itself uses.
3. Upserts one doc per product into `products` with a status: ok / not_found / error.

Safe to re-run: products already `ok` or `not_found` are skipped, so a crash
only costs the in-flight requests. Failed products are retried in slower rounds.

Usage (on the VM, from the repo root):
    uv run ingest/crawl_products.py             # full crawl
    uv run ingest/crawl_products.py --limit 20  # quick test
    uv run ingest/crawl_products.py --workers 8 # faster (more risk of being rate-limited)
"""

import argparse
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from curl_cffi import requests
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from tqdm import tqdm

# --- Config ---------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

SOURCE = "summary"
IDS = "product_ids"
TARGET = "products"
API_URL = "https://www.glamira.com/productcustomizer/reactdata/index/id/{}/"  # .com = English names

PRODUCT_EVENTS = [
    "view_product_detail",
    "select_product_option",
    "select_product_option_quality",
    "add_to_cart_action",
    "product_detail_recommendation_visible",
    "product_detail_recommendation_noticed",
    "product_view_all_recommend_clicked",  # stores the id in viewing_product_id
]

# Each round retries what the previous one failed, slower and with fewer workers.
ROUNDS = [  # (min delay s, max delay s, workers)
    (1.0, 2.0, 4),
    (5.0, 8.0, 2),
    (10.0, 15.0, 1),
]

# Fields copied to the top level; the full response is kept in `raw`.
FIELDS = [
    "name", "sku", "attribute_set", "type_id", "product_type", "collection", "collection_id",
    "gender", "category", "category_name", "price", "min_price", "max_price", "store_code",
]

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)


def connect():
    """Return the glamira database. Password is URL-encoded because it may contain # / + =."""
    user = quote_plus(os.environ["MONGO_USER"])
    password = quote_plus(os.environ["MONGO_PASSWORD"])
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    client = MongoClient(f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin")
    return client[os.getenv("MONGO_DB", "glamira")]


def build_product_ids(db):
    """Write unique product ids to `product_ids` once (full scan of 41M docs, ~10 min)."""
    if db[IDS].estimated_document_count() > 0:
        log.info("%s already built, skipping", IDS)
        return
    log.info("Building %s from %s (about 10 minutes)", IDS, SOURCE)
    db[SOURCE].aggregate([
        {"$match": {"collection": {"$in": PRODUCT_EVENTS}}},
        {"$project": {"product_id": {"$cond": [
            {"$eq": ["$collection", "product_view_all_recommend_clicked"]},
            "$viewing_product_id",
            "$product_id",
        ]}}},
        {"$match": {"product_id": {"$nin": [None, ""]}}},
        {"$group": {"_id": {"$toString": "$product_id"}}},
        {"$project": {"_id": 0, "product_id": "$_id"}},
        {"$out": IDS},
    ], allowDiskUse=True)


def pending_ids(db):
    """Ids not yet crawled. `error` ones are retried; `ok` and `not_found` are final."""
    done = set(db[TARGET].distinct("product_id", {"status": {"$in": ["ok", "not_found"]}}))
    all_ids = db[IDS].distinct("product_id")
    return [pid for pid in all_ids if pid not in done]


def fetch(product_id, delay):
    """Fetch one product. Returns the doc to save; never raises."""
    time.sleep(delay)
    doc = {"product_id": product_id, "crawled_at": datetime.now(timezone.utc)}
    try:
        # impersonate="chrome" copies Chrome's TLS handshake; plain requests gets 403 from Akamai.
        r = requests.get(API_URL.format(product_id), impersonate="chrome", timeout=20)
    except Exception as e:
        return doc | {"status": "error", "error": f"request failed: {str(e)[:200]}"}

    if r.status_code == 404:
        return doc | {"status": "not_found"}
    if r.status_code == 429:
        time.sleep(30)  # rate limited: pause this worker before the next request
    if r.status_code != 200:
        return doc | {"status": "error", "error": f"HTTP {r.status_code}"}

    try:
        data = r.json()
    except ValueError:
        return doc | {"status": "error", "error": "response is not JSON"}
    if not isinstance(data, dict) or not data.get("name"):
        return doc | {"status": "error", "error": "JSON has no name"}

    return doc | {"status": "ok", **{f: data.get(f) for f in FIELDS}, "raw": data}


def run_round(db, ids, round_num, delay_min, delay_max, workers, done=None):
    """Crawl ids concurrently, save each result as it arrives. Returns ids that errored.

    `done` = {"ok": n, "not_found": n} from earlier runs, so the bar shows overall progress.
    """
    log.info("Round %d: %s products, %d workers, %.0f-%.0fs delay",
             round_num, f"{len(ids):,}", workers, delay_min, delay_max)
    counts = {"ok": 0, "not_found": 0, **(done or {}), "error": 0}
    already = sum(counts.values())
    failed = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch, pid, random.uniform(delay_min, delay_max)) for pid in ids]
        bar = tqdm(as_completed(futures), total=already + len(ids), initial=already,
                   unit="product", desc=f"Round {round_num}")
        for future in bar:
            doc = future.result()
            db[TARGET].replace_one({"product_id": doc["product_id"]}, doc, upsert=True)
            counts[doc["status"]] += 1
            if doc["status"] == "error":
                failed.append(doc["product_id"])
            bar.set_postfix(counts, refresh=False)
            if doc["status"] == "ok":
                bar.write(f"  ok  {doc['product_id']:>7}  {doc['name']}")
            else:
                bar.write(f"  {doc['status']:<9} {doc['product_id']:>7}  {doc.get('error', '')}")

    log.info("Round %d done: ok=%s not_found=%s error=%s",
             round_num, counts["ok"], counts["not_found"], counts["error"])
    return failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="crawl only N products (for testing)")
    parser.add_argument("--workers", type=int, default=ROUNDS[0][2], help="parallel workers in round 1")
    args = parser.parse_args()

    db = connect()
    build_product_ids(db)
    db[TARGET].create_index([("product_id", ASCENDING)], unique=True)

    ids = pending_ids(db)
    done = {s: db[TARGET].count_documents({"status": s}) for s in ("ok", "not_found")}
    log.info("%s products to crawl, %s already done", f"{len(ids):,}", f"{sum(done.values()):,}")
    if args.limit:
        ids = ids[: args.limit]

    rounds = [(*ROUNDS[0][:2], args.workers), *ROUNDS[1:]]
    for round_num, (delay_min, delay_max, workers) in enumerate(rounds, start=1):
        if not ids:
            break
        # Round 1 continues the overall count; retry rounds count only their own retries.
        ids = run_round(db, ids, round_num, delay_min, delay_max, workers,
                        done=done if round_num == 1 else None)

    summary = {s: db[TARGET].count_documents({"status": s}) for s in ("ok", "not_found", "error")}
    log.info("Done: %s", summary)


if __name__ == "__main__":
    main()
