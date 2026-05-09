import os

# ── MongoDB ──────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("DB_NAME", "countly")

# ── Collections ──────────────────────────────────────
UNIQUE_IP_COLLECTION      = os.getenv("UNIQUE_IP_COLLECTION", "unique_ips")
IP_OUTPUT_COLLECTION      = os.getenv("IP_OUTPUT_COLLECTION", "ip_locations")
SUMMARY_COLLECTION        = os.getenv("SUMMARY_COLLECTION", "summary")
PRODUCT_INPUT_COLLECTION  = os.getenv("PRODUCT_INPUT_COLLECTION", "product_urls")
PRODUCT_OUTPUT_COLLECTION = os.getenv("PRODUCT_OUTPUT_COLLECTION", "product_names")

# ── Local paths ───────────────────────────────────────
# Base directory for all data outputs. Override with DATA_DIR env var.
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))

IP2LOCATION_BIN_PATH  = os.getenv("IP2LOCATION_BIN_PATH", os.path.join(DATA_DIR, "raw", "ip2location.bin"))
IP_OUTPUT_CSV         = os.getenv("IP_OUTPUT_CSV",         os.path.join(DATA_DIR, "processed", "ip_locations.csv"))
SUMMARY_OUTPUT_DIR    = os.getenv("SUMMARY_OUTPUT_DIR",    os.path.join(DATA_DIR, "processed", "summary"))
PRODUCT_OUTPUT_CSV    = os.getenv("PRODUCT_OUTPUT_CSV",    os.path.join(DATA_DIR, "processed", "product_names.csv"))
PRODUCT_LOG_FILE      = os.getenv("PRODUCT_LOG_FILE",      os.path.join(DATA_DIR, "processed", "crawl_errors.log"))

# ── GCS ───────────────────────────────────────────────
GCS_SUMMARY_PATH = os.getenv("GCS_SUMMARY_PATH", "gs://unigap/glamira-data/processed/summary/")

# ── Processing ────────────────────────────────────────
IP_BATCH_SIZE      = int(os.getenv("IP_BATCH_SIZE",      "10000"))
SUMMARY_BATCH_SIZE = int(os.getenv("SUMMARY_BATCH_SIZE", "100000"))
