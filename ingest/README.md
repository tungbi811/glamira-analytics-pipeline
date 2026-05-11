# Ingestion Pipeline

Prepares raw Glamira UBL data for the analytics pipeline. Run steps in order.

## Overview

| Step | Folder | What it does |
|---|---|---|
| 1 | `01_mongodb_import/` | Download raw data from GCS and import into MongoDB |
| 2 | `02_ip_geolocation/` | Extract unique IPs and enrich with location data |
| 3 | `03_product_crawler/` | Extract product URLs and crawl product details |

## Prerequisites

- `gcloud` CLI authenticated (`gcloud auth login`)
- MongoDB running (`sudo systemctl start mongod`)
- `mongodb-database-tools` installed (`sudo apt install -y mongodb-database-tools`)
- Python dependencies: `uv add pymongo IP2Location beautifulsoup4 curl-cffi`

---

## Step 1 — MongoDB Import

```bash
bash ingestion/01_mongodb_import/import_data.sh
```

See `01_mongodb_import/README.md` for details.

---

## Step 2 — IP Geolocation

Extract 3,239,628 unique IPs into a separate collection, then enrich with country/region/city.

```bash
# Extract unique IPs from summary into unique_ips collection
./ingestion/mongo.sh ingestion/02_ip_geolocation/extract_unique_ips.js

# Enrich with location data → writes to ip_locations collection
nohup uv run python ingestion/02_ip_geolocation/lookup_ip_locations.py > logs/lookup_ip.log 2>&1 &
tail -f logs/lookup_ip.log
```

---

## Step 3 — Product Crawler

Extract 19,418 unique product URLs, then crawl each for product details. 18,987 successfully crawled, 431 not found (404 — products no longer exist on Glamira's site).

```bash
# Extract unique product URLs → writes to product_urls collection
./ingestion/mongo.sh ingestion/03_product_crawler/extract_product_urls.js

# Crawl product details → writes to product_details collection
# Resumable: re-running skips already crawled products
nohup uv run python ingestion/03_product_crawler/crawl_product_details.py > logs/crawl.log 2>&1 &
tail -f logs/crawl.log
```

---

## Running mongo.sh scripts

`ingestion/mongo.sh` connects to the MongoDB host defined by `VM_EXTERNAL_IP` in `.env`:

```bash
./ingestion/mongo.sh <path-to-script.js>
```
