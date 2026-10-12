"""Look up the location of every unique IP in the events and save it to MongoDB.

Reads distinct IPs from `summary`, resolves each with the IP2Location DB3 file
(country, region, city), and writes `ip_locations`. Safe to re-run: it builds a
temp collection and swaps it in, so a failed run never leaves a half-written table.

Usage (on the VM, from the repo root):
    uv run extract/lookup_ips.py
"""

import logging
import os
import subprocess
from pathlib import Path
from urllib.parse import quote_plus

import IP2Location
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient

# --- Config ---------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

BIN_NAME = "ip2location_db3.bin"
BIN_PATH = Path.home() / "data" / BIN_NAME
SOURCE = "summary"
TARGET = "ip_locations"
BATCH_SIZE = 10_000

# What IP2Location returns when it can't resolve an IP.
UNKNOWN = {"-", "INVALID IP ADDRESS", "IPV6 ADDRESS MISSING IN IPV4 BIN"}

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


def download_bin():
    """Fetch the IP2Location file from GCS if it isn't on disk yet."""
    if BIN_PATH.exists():
        log.info("%s already downloaded, skipping", BIN_NAME)
        return
    BIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    src = f"{os.environ['GCS_BUCKET']}/source/{BIN_NAME}"
    log.info("Downloading %s", src)
    subprocess.run(["gcloud", "storage", "cp", src, str(BIN_PATH)], check=True)


def unique_ips(db):
    """Yield each distinct IP. $group streams results; .distinct() would hit the 16 MB limit."""
    cursor = db[SOURCE].aggregate([{"$group": {"_id": "$ip"}}], allowDiskUse=True)
    for doc in cursor:
        if doc["_id"]:  # skip missing / empty ip
            yield doc["_id"]


def clean(value):
    """Turn IP2Location's 'unknown' markers into None."""
    return None if value in UNKNOWN else value


def lookup(ip2loc, ip):
    rec = ip2loc.get_all(ip)
    if rec is None:
        return {"ip": ip, "country_code": None, "country": None, "region": None, "city": None}
    return {
        "ip": ip,
        "country_code": clean(rec.country_short),
        "country": clean(rec.country_long),
        "region": clean(rec.region),
        "city": clean(rec.city),
    }


def main():
    download_bin()
    db = connect()
    ip2loc = IP2Location.IP2Location(str(BIN_PATH))

    tmp = db[f"{TARGET}_tmp"]
    tmp.drop()

    log.info("Reading unique IPs from %s (a few minutes on 41M docs)", SOURCE)
    batch, total, unresolved = [], 0, 0
    for ip in unique_ips(db):
        row = lookup(ip2loc, ip)
        unresolved += row["country_code"] is None
        batch.append(row)
        if len(batch) == BATCH_SIZE:
            tmp.insert_many(batch, ordered=False)
            total += len(batch)
            batch = []
            if total % 500_000 == 0:
                log.info("%s IPs done", f"{total:,}")
    if batch:
        tmp.insert_many(batch, ordered=False)
        total += len(batch)

    tmp.create_index([("ip", ASCENDING)], unique=True)
    tmp.rename(TARGET, dropTarget=True)  # atomic swap: old table stays until the new one is complete
    ip2loc.close()

    log.info("Done: %s IPs saved to %s, %s without a location", f"{total:,}", TARGET, f"{unresolved:,}")


if __name__ == "__main__":
    main()
