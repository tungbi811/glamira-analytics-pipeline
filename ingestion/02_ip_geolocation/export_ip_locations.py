import pymongo
import csv
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import MONGO_URI, DB_NAME, IP_OUTPUT_CSV

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]

print("Exporting ip_locations...")
output = IP_OUTPUT_CSV

with open(output, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["ip", "country_code", "country_name", "region", "city"])
    writer.writeheader()
    for doc in db.ip_locations.find({}, {"_id": 0, "ip": 1, "country_code": 1, "country_name": 1, "region": 1, "city": 1}):
        writer.writerow(doc)

print("Done!")
client.close()
