import IP2Location
import pymongo
import csv
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    MONGO_URI, DB_NAME,
    UNIQUE_IP_COLLECTION,
    IP_OUTPUT_COLLECTION as OUTPUT_COLLECTION,
    IP_OUTPUT_CSV        as OUTPUT_CSV,
    IP2LOCATION_BIN_PATH as BIN_PATH,
    IP_BATCH_SIZE        as BATCH_SIZE,
)

FIELDS = ["ip", "country_code", "country_name", "region", "city"]

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
ip2loc = IP2Location.IP2Location(BIN_PATH)

total = db[UNIQUE_IP_COLLECTION].count_documents({})
print(f"Total unique IPs: {total:,}")

out_col = db[OUTPUT_COLLECTION]
out_col.drop()

processed = 0
errors = 0
batch = []

def flush(batch, writer, csvfile):
    out_col.insert_many(batch)
    writer.writerows(batch)
    csvfile.flush()

with open(OUTPUT_CSV, "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
    writer.writeheader()

    cursor = db[UNIQUE_IP_COLLECTION].find({}, {"_id": 0, "ip": 1}).batch_size(BATCH_SIZE)

    for doc in cursor:
        ip = doc.get("ip", "")
        if not ip or ip == "-":
            errors += 1
            continue

        try:
            rec = ip2loc.get_all(ip)
            batch.append({
                "ip":           ip,
                "country_code": rec.country_short,
                "country_name": rec.country_long,
                "region":       rec.region,
                "city":         rec.city,
            })
        except Exception:
            errors += 1
            continue

        if len(batch) >= BATCH_SIZE:
            flush(batch, writer, csvfile)
            processed += len(batch)
            batch = []
            print(f"  Processed {processed:,} / {total:,}")

    if batch:
        flush(batch, writer, csvfile)
        processed += len(batch)

print(f"Done! Processed {processed:,}, errors {errors:,}")
client.close()