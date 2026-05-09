import os

# MONGO_URI takes precedence; falls back to constructing from VM_EXTERNAL_IP so .env only needs one entry
_host     = os.getenv("VM_EXTERNAL_IP", "localhost")
MONGO_URI = os.getenv("MONGO_URI", f"mongodb://{_host}:27017")
DB_NAME   = os.getenv("DB_NAME", "countly")

SUMMARY_COLLECTION        = os.getenv("SUMMARY_COLLECTION",        "summary")
IP_OUTPUT_COLLECTION      = os.getenv("IP_OUTPUT_COLLECTION",      "ip_locations")
PRODUCT_OUTPUT_COLLECTION = os.getenv("PRODUCT_OUTPUT_COLLECTION", "product_details")

DATA_DIR                  = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
SUMMARY_OUTPUT_DIR        = os.getenv("SUMMARY_OUTPUT_DIR",        os.path.join(DATA_DIR, "processed", "summary"))
IP_OUTPUT_DIR             = os.getenv("IP_OUTPUT_DIR",             os.path.join(DATA_DIR, "processed", "ip_locations"))
PRODUCT_OUTPUT_DIR        = os.getenv("PRODUCT_OUTPUT_DIR",        os.path.join(DATA_DIR, "processed", "product_details"))

GCS_SUMMARY_PATH          = os.getenv("GCS_SUMMARY_PATH",          "gs://unigap/glamira-data/processed/summary/")
GCS_IP_PATH               = os.getenv("GCS_IP_PATH",               "gs://unigap/glamira-data/processed/ip_locations/")
GCS_PRODUCT_PATH          = os.getenv("GCS_PRODUCT_PATH",          "gs://unigap/glamira-data/processed/product_details/")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100000"))
