import os

# MONGO_URI takes precedence; falls back to constructing from VM_EXTERNAL_IP so .env only needs one entry
_host     = os.getenv("VM_EXTERNAL_IP", "localhost")
MONGO_URI = os.getenv("MONGO_URI", f"mongodb://{_host}:27017")
DB_NAME   = os.getenv("DB_NAME", "countly")

# ── Collections ──────────────────────────────────────
UNIQUE_IP_COLLECTION      = os.getenv("UNIQUE_IP_COLLECTION", "unique_ips")
IP_OUTPUT_COLLECTION      = os.getenv("IP_OUTPUT_COLLECTION", "ip_locations")
SUMMARY_COLLECTION        = os.getenv("SUMMARY_COLLECTION", "summary")
PRODUCT_INPUT_COLLECTION  = os.getenv("PRODUCT_INPUT_COLLECTION", "product_urls")
PRODUCT_OUTPUT_COLLECTION = os.getenv("PRODUCT_OUTPUT_COLLECTION", "product_details")

# ── Local paths ───────────────────────────────────────
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
LOGS_DIR = os.getenv("LOGS_DIR", os.path.join(os.path.dirname(__file__), "..", "logs"))

IP2LOCATION_BIN_PATH  = os.getenv("IP2LOCATION_BIN_PATH", os.path.join(DATA_DIR, "raw", "ip2location.bin"))
SUMMARY_OUTPUT_DIR    = os.getenv("SUMMARY_OUTPUT_DIR",    os.path.join(DATA_DIR, "processed", "summary"))
PRODUCT_LOG_FILE      = os.getenv("PRODUCT_LOG_FILE",      os.path.join(LOGS_DIR, "crawl_errors.log"))

# ── GCS ───────────────────────────────────────────────
GCS_SUMMARY_PATH = os.getenv("GCS_SUMMARY_PATH", "gs://unigap/glamira-data/processed/summary/")

# ── Processing ────────────────────────────────────────
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100000"))
