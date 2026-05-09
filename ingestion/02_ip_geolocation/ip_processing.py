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

# Connect to MongoDB
print("Connecting to MongoDB...")
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]

# Get total count for progress tracking
total = db[UNIQUE_IP_COLLECTION].count_documents({})
print(f"Total unique IPs to process: {total:,}")

# Load ip2location database
print("Loading ip2location database...")
ip2loc = IP2Location.IP2Location(BIN_PATH)

# Prepare output collection
out_col = db[OUTPUT_COLLECTION]
out_col.drop()

# Open CSV file once, write in streaming fashion
print("Processing IPs...")
processed = 0
errors = 0
batch = []

with open(OUTPUT_CSV, "w", newline="") as csvfile:
    writer = None  # will be created after first result

    # ← cursor reads from MongoDB one batch at a time, not all at once
    cursor = db[UNIQUE_IP_COLLECTION].find(
        {}, {"_id": 0, "ip": 1}
    ).batch_size(BATCH_SIZE)

    for doc in cursor:
        ip = doc.get("ip", "")

        if not ip or ip == "-":
            errors += 1
            continue

        try:
            rec = ip2loc.get_all(ip)
            result = {
                "ip": ip,
                "country_code": rec.country_short,
                "country_name": rec.country_long,
                "region": rec.region,
                "city": rec.city,
            }
            batch.append(result)

            # Write CSV header on first result
            if writer is None:
                writer = csv.DictWriter(csvfile, fieldnames=result.keys())
                writer.writeheader()

        except Exception as e:
            errors += 1

        # When batch is full — flush to MongoDB and CSV, then clear
        if len(batch) >= BATCH_SIZE:
            out_col.insert_many(batch)
            writer.writerows(batch)
            csvfile.flush()               # force write to disk
            processed += len(batch)
            batch = []                    # ← clear batch from RAM
            print(f"  Processed {processed:,} / {total:,} IPs...")

    # Handle remaining IPs that didn't fill a full batch
    if batch:
        out_col.insert_many(batch)
        writer.writerows(batch)
        processed += len(batch)

print(f"Done! Processed {processed:,} IPs, {errors:,} errors")
print(f"Saved to MongoDB collection '{OUTPUT_COLLECTION}' and '{OUTPUT_CSV}'")
client.close()
