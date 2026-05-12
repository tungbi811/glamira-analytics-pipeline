# Setup Guide

Step-by-step guide to get the project running on a fresh compute instance (Ubuntu 24.04).

---

## 1. Install MongoDB 8.2

```bash
sudo apt-get install -y gnupg curl

curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc \
  | sudo gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor

echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.2 multiverse" \
  | sudo tee /etc/apt/sources.list.d/mongodb-org-8.2.list

sudo apt update
sudo apt install -y mongodb-org mongodb-database-tools

sudo systemctl start mongod
sudo systemctl enable mongod
```

---

## 2. Clone the Repository

```bash
git clone <repo-url>
cd glamira_analytics_pipeline
```

---

## 3. Configure Environment Variables

Create a `.env` file at the project root (never commit this file):

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
VM_EXTERNAL_IP=localhost
MONGO_URI=mongodb://localhost:27017
DB_NAME=countly
DATA_DIR=data
LOGS_DIR=logs
GCS_SUMMARY_PATH=gs://unigap/glamira-data/processed/summary/
GCS_IP_PATH=gs://unigap/glamira-data/processed/ip_locations/
GCS_PRODUCT_PATH=gs://unigap/glamira-data/processed/product_details/
IP2LOCATION_BIN_PATH=data/raw/ip2location.bin
```

> The Python scripts load values from the project-root `.env` via `utils.py`. Required variables are listed in `.env.example`; missing values fail fast at startup.

---

## 4. Download Raw Data and Import into MongoDB

Authenticate with GCP, then run the init script:

```bash
gcloud auth login

bash ingestion/01_mongodb_import/init_data.sh
```

This will:
1. Download `glamira_ubl_oct_nov_2019.tar.gz` and `ip_country_region_city.bin` from GCS into `data/raw/`
2. Extract the tar into `data/raw/dump/`
3. Import the dump into the `countly` MongoDB database

Each step is skipped automatically if already completed.

---

## 5. Install Python Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## 6. Run Ingestion Scripts

Run each script in order:

```bash
# 1. Process IP geolocation
python ingestion/ip_geolocation/ip_processing.py

# 2. Export summary data to GCS
python ingestion/mongodb_import/export_summary.py

# 3. Crawl product names
python ingestion/product_crawler/curlffi_crawl_no_proxy.py
```
