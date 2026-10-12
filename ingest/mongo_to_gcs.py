"""Export MongoDB collections to Parquet files in GCS, ready for BigQuery.

Each run writes one folder per table:
    gs://<bucket>/export/<table>/<run_id>/part-00001.parquet
    gs://<bucket>/export/<table>/<run_id>/_SUCCESS     <- written last

The Cloud Function loads a folder only when `_SUCCESS` appears, so a failed or
half-finished export is never loaded. Re-running creates a new run folder.

Every value is STRING (raw layer). The source has mixed types (ids are text
or numbers, `price` is locale-formatted text), so typing is left to dbt.

Special cases in `summary`:
- `option` comes in several shapes (list of option records, a flat dict like
  {"alloy": "white-585"}, a list of such dicts, a scalar). All are normalized to
  one list of {option_label, option_id, value_label, value_id}.
- `cart_products` becomes a list of {product_id, amount, price, currency, option},
  with its inner `option` normalized the same way.
- Both are always a list (empty when missing), matching BigQuery REPEATED RECORD.
Other objects (`products.raw`) become JSON strings. Fields not listed in TABLES
go to `_extra` as JSON, so nothing is dropped.

Usage (on the VM, from the repo root):
    uv run ingest/mongo_to_gcs.py ip_locations      # one table (~2 min, good test)
    uv run ingest/mongo_to_gcs.py                   # all tables (~40 min)
"""

import argparse
import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import pyarrow as pa
import pyarrow.parquet as pq
from bson import ObjectId
from dotenv import load_dotenv
from google.cloud import storage
from pymongo import MongoClient
from tqdm import tqdm

# --- Config ---------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

PREFIX = "export"
ROWS_PER_PART = 250_000  # ~20-40 MB per Parquet file; keeps memory low on e2-standard-2
EXTRA = "_extra"

# Columns per table, in BigQuery column order. See docs/data_dictionary.md.
TABLES = {
    "summary": [
        "_id", "collection", "time_stamp", "local_time", "ip", "user_agent", "resolution",
        "device_id", "user_id_db", "email_address", "store_id", "api_version",
        "current_url", "referrer_url", "show_recommendation",
        "product_id", "option", "price", "currency", "is_paypal", "cat_id",
        "order_id", "cart_products",
        "viewing_product_id", "recommendation_product_id", "recommendation_clicked_position",
        "recommendation_product_position", "recommendation", "utm_source", "utm_medium", "key_search", "collect_id",
    ],
    "ip_locations": ["ip", "country_code", "country", "region", "city"],
    "products": [
        "product_id", "status", "error", "crawled_at",
        "name", "sku", "attribute_set", "type_id", "product_type", "collection", "collection_id",
        "gender", "category", "category_name", "price", "min_price", "max_price", "store_code",
        "raw",
    ],
}

# Nested columns (summary only). Everything else is a plain string.
OPTION_FIELDS = ["option_label", "option_id", "value_label", "value_id"]
OPTION = pa.struct([(f, pa.string()) for f in OPTION_FIELDS])
CART_FIELDS = ["product_id", "amount", "price", "currency"]
CART_ITEM = pa.struct([*[(f, pa.string()) for f in CART_FIELDS], ("option", pa.list_(OPTION))])
NESTED = {"option": pa.list_(OPTION), "cart_products": pa.list_(CART_ITEM)}

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)


def connect():
    """Return the glamira database. Password is URL-encoded because it may contain # / + =."""
    user = quote_plus(os.environ["MONGO_USER"])
    password = quote_plus(os.environ["MONGO_PASSWORD"])
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    # tz_aware: datetimes come back as UTC-aware, so isoformat() includes +00:00
    client = MongoClient(f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin", tz_aware=True)
    return client[os.getenv("MONGO_DB", "glamira")]


def to_text(value):
    """Convert any BSON value to a string (None stays None)."""
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):  # before int: bool is a subclass of int
        return "true" if value else "false"
    if isinstance(value, (int, float, ObjectId)):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return json.dumps(value, default=str, ensure_ascii=False)  # arrays, objects


def normalize_option(value):
    """Return `option` as a list of {option_label, option_id, value_label, value_id}, whatever its shape."""
    if not value:
        return []
    if not isinstance(value, list):
        value = [value]
    out = []
    for item in value:
        if isinstance(item, dict) and "option_label" in item:  # usual shape
            out.append({f: to_text(item.get(f)) for f in OPTION_FIELDS})
        elif isinstance(item, dict):  # flat {label: value}, e.g. {"alloy": "white-585"}
            out.extend({"option_label": to_text(k), "option_id": None, "value_label": to_text(v), "value_id": None}
                       for k, v in item.items())
        else:  # bare value
            out.append({"option_label": to_text(item), "option_id": None, "value_label": None, "value_id": None})
    return out


def normalize_cart(value):
    """Return `cart_products` as a list of {product_id, amount, price, currency, option}."""
    if not value:
        return []
    if not isinstance(value, list):
        value = [value]
    return [{**{f: to_text(item.get(f)) for f in CART_FIELDS}, "option": normalize_option(item.get("option"))}
            for item in value if isinstance(item, dict)]


CONVERTERS = {"option": normalize_option, "cart_products": normalize_cart}


def to_row(doc, columns):
    """Pick the known columns; anything else goes to `_extra` as JSON."""
    row = {col: CONVERTERS.get(col, to_text)(doc.pop(col, None)) for col in columns}
    doc.pop("_id", None)  # only kept when listed (summary)
    row[EXTRA] = to_text(doc) if doc else None
    return row


def upload_part(bucket, path, rows, schema):
    """Write rows to an in-memory Parquet file and upload it."""
    table = pa.Table.from_pylist(rows, schema=schema)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    buf.seek(0)
    bucket.blob(path).upload_from_file(buf, content_type="application/octet-stream")


def export_table(db, bucket, name, run_id):
    columns = TABLES[name]
    schema = pa.schema([(col, NESTED.get(col, pa.string())) for col in [*columns, EXTRA]])
    folder = f"{PREFIX}/{name}/{run_id}"
    total = db[name].estimated_document_count()
    log.info("Exporting %s (%s docs) to gs://%s/%s/", name, f"{total:,}", bucket.name, folder)

    rows, parts, count = [], 0, 0
    with tqdm(total=total, unit="doc", desc=name) as bar:
        for doc in db[name].find({}, batch_size=10_000):
            rows.append(to_row(doc, columns))
            if len(rows) == ROWS_PER_PART:
                parts += 1
                upload_part(bucket, f"{folder}/part-{parts:05d}.parquet", rows, schema)
                count += len(rows)
                bar.update(len(rows))
                rows = []
        if rows:
            parts += 1
            upload_part(bucket, f"{folder}/part-{parts:05d}.parquet", rows, schema)
            count += len(rows)
            bar.update(len(rows))

    # Written last: the Cloud Function loads the folder when this file appears.
    marker = {"table": name, "run_id": run_id, "rows": count, "parts": parts}
    bucket.blob(f"{folder}/_SUCCESS").upload_from_string(json.dumps(marker), content_type="application/json")
    log.info("Done %s: %s rows in %d parts", name, f"{count:,}", parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tables", nargs="*", default=list(TABLES),
                        help=f"tables to export: {', '.join(TABLES)} (default: all)")
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"),
                        help="folder name for this export (default: current UTC time)")
    args = parser.parse_args()
    unknown = set(args.tables) - set(TABLES)
    if unknown:
        parser.error(f"unknown table(s): {', '.join(sorted(unknown))}")

    db = connect()
    bucket = storage.Client().bucket(os.environ["GCS_BUCKET"].removeprefix("gs://"))
    for name in args.tables:
        export_table(db, bucket, name, args.run_id)


if __name__ == "__main__":
    main()
