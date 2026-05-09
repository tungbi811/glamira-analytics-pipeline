# 01 — MongoDB Import

Downloads raw data from GCS, extracts it, and imports it into MongoDB.

## Usage

```bash
bash ingestion/01_mongodb_import/import_data.sh
```

## What it does

1. Downloads `glamira_ubl_oct_nov_2019.tar.gz` and `ip_country_region_city.bin` from GCS into `data/raw/`
2. Extracts the tar into `data/raw/dump/`
3. Imports the dump into the `countly` MongoDB database

Each step is skipped automatically if it has already been completed.

## Prerequisites

- `gcloud` CLI authenticated (`gcloud auth login`)
- MongoDB running (`sudo systemctl start mongod`)
- `mongodb-database-tools` installed (`sudo apt install -y mongodb-database-tools`)
