import json
import os
import time
import subprocess
import sys
import pymongo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    MONGO_URI, DB_NAME, BATCH_SIZE,
    SUMMARY_COLLECTION,        SUMMARY_OUTPUT_DIR,  GCS_SUMMARY_PATH,
    IP_OUTPUT_COLLECTION,      IP_OUTPUT_DIR,       GCS_IP_PATH,
    PRODUCT_OUTPUT_COLLECTION, PRODUCT_OUTPUT_DIR,  GCS_PRODUCT_PATH,
)

# BigQuery REPEATED RECORD fields must always be arrays — even when absent in MongoDB
SUMMARY_ARRAY_FIELDS = ["option", "cart_products"]

EXPORTS = [
    (SUMMARY_COLLECTION,        SUMMARY_OUTPUT_DIR,  GCS_SUMMARY_PATH,  SUMMARY_ARRAY_FIELDS),
    (IP_OUTPUT_COLLECTION,      IP_OUTPUT_DIR,       GCS_IP_PATH,       None),
    (PRODUCT_OUTPUT_COLLECTION, PRODUCT_OUTPUT_DIR,  GCS_PRODUCT_PATH,  None),
]


def safe_str(val):
    """Convert any value to string, returning empty string for None."""
    if val is None:
        return ""
    return str(val)

def normalize_option(value):
    """Normalize the option field into a consistent array of {option_label, option_id, value_label, value_id}.
    Raw data has three formats: array of dicts, plain dict, or scalar — all are converted to the same structure."""
    if not value:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                if "option_label" in item:
                    result.append({
                        "option_label": safe_str(item.get("option_label")),
                        "option_id":    safe_str(item.get("option_id")),
                        "value_label":  safe_str(item.get("value_label")),
                        "value_id":     safe_str(item.get("value_id")),
                    })
                else:
                    for k, v in item.items():
                        result.append({
                            "option_label": safe_str(k),
                            "option_id":    "",
                            "value_label":  safe_str(v),
                            "value_id":     ""
                        })
            else:
                result.append({
                    "option_label": safe_str(item),
                    "option_id":    "",
                    "value_label":  "",
                    "value_id":     ""
                })
        return result
    if isinstance(value, dict):
        return [
            {"option_label": safe_str(k), "option_id": "", "value_label": safe_str(v), "value_id": ""}
            for k, v in value.items()
        ]
    return []

def flatten_list(lst):
    """Recursively flatten a list, converting all values to strings and normalizing nested option fields."""
    if not lst:
        return []
    result = []
    for item in lst:
        if isinstance(item, dict):
            flat_item = {}
            for k, v in item.items():
                if k == "option":
                    flat_item[k] = normalize_option(v)
                elif isinstance(v, list):
                    flat_item[k] = flatten_list(v)
                elif isinstance(v, dict):
                    flat_item[k] = flatten_list([v])
                else:
                    flat_item[k] = safe_str(v)
            result.append(flat_item)
        else:
            result.append(safe_str(item))
    return result

def flatten_doc(doc, always_array_fields=None):
    """Flatten a MongoDB document to a JSON-serializable dict compatible with BigQuery schema."""
    result = {}
    for key, value in doc.items():
        if key == "_id":
            result[key] = str(value)
        elif key == "option":
            result[key] = normalize_option(value)
        elif isinstance(value, list):
            result[key] = flatten_list(value)
        elif isinstance(value, dict):
            result[key] = flatten_list([value])
        else:
            result[key] = safe_str(value)

    for field in (always_array_fields or []):
        if field not in result or result[field] is None:
            result[field] = []

    return result

def get_completed_batches(gcs_path, collection_name):
    """Return the number of already uploaded batches by listing existing files in GCS."""
    import re
    result = subprocess.run(
        ["gcloud", "storage", "ls", gcs_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return 0
    files = result.stdout.strip().split("\n")
    numbers = [
        int(m.group(1))
        for f in files
        if (m := re.search(rf"{collection_name}_part_(\d+)\.jsonl", f))
    ]
    return max(numbers) if numbers else 0

def run_export(collection_name, output_dir, gcs_path, always_array_fields=None):
    """Export a MongoDB collection to GCS as JSONL files in batches. Resumes from the last uploaded batch if interrupted."""
    os.makedirs(output_dir, exist_ok=True)

    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[collection_name]

    total = collection.count_documents({})
    completed_batches = get_completed_batches(gcs_path, collection_name)
    docs_to_skip = completed_batches * BATCH_SIZE

    print(f"\nCollection     : {collection_name}")
    print(f"Total documents: {total:,}")
    print(f"Batch size     : {BATCH_SIZE:,}")
    print(f"Expected files : {(total // BATCH_SIZE) + 1}")
    if completed_batches:
        print(f"Resuming from  : batch {completed_batches + 1} (skipping {docs_to_skip:,} docs)")
    print("-" * 60)

    start_time = time.time()
    batch_num = completed_batches
    written = 0
    upload_failed = []

    def write_and_upload(batch):
        """Write a batch to a local JSONL file, upload to GCS, then delete the local file."""
        nonlocal batch_num  # += rebinds the integer so nonlocal is required; upload_failed.append() mutates in-place so it is not
        batch_num += 1
        filename = f"{output_dir}/{collection_name}_part_{batch_num:04d}.jsonl"
        with open(filename, "w", encoding="utf-8") as f:
            for record in batch:
                f.write(json.dumps(record, default=str) + "\n")

        result = subprocess.run(
            ["gcloud", "storage", "cp", filename, gcs_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  → Uploaded successfully!")
            os.remove(filename)
        else:
            print(f"  → Upload FAILED: {result.stderr[:200]}")
            upload_failed.append(filename)

    # no_cursor_timeout=True prevents the server from closing the cursor during long exports
    cursor = collection.find({}, no_cursor_timeout=True).skip(docs_to_skip).batch_size(BATCH_SIZE)

    try:
        batch = []
        for doc in cursor:
            batch.append(flatten_doc(doc, always_array_fields))

            if len(batch) >= BATCH_SIZE:
                written += len(batch)
                elapsed = time.time() - start_time
                rate = written / elapsed
                remaining = (total - written) / rate if rate > 0 else 0
                print(f"[{batch_num + 1}] Written {written:,}/{total:,} | Rate: {rate:.0f} docs/s | ETA: {remaining/60:.1f} min")
                write_and_upload(batch)
                batch = []

        if batch:
            written += len(batch)
            print(f"[{batch_num + 1}] Final batch — written {written:,}/{total:,}")
            write_and_upload(batch)

    finally:
        cursor.close()
        client.close()

    elapsed = time.time() - start_time
    hours, rem = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(rem, 60)

    print(f"\n{'='*60}")
    print(f"DONE — {collection_name}")
    print(f"  Total written  : {written:,}")
    print(f"  Total files    : {batch_num}")
    print(f"  Upload failed  : {len(upload_failed)}")
    print(f"  Total time     : {hours}h {minutes}m {seconds}s")
    print(f"  GCS path       : {gcs_path}")
    if upload_failed:
        print(f"\nFailed uploads — retry manually:")
        for f in upload_failed:
            print(f"  gcloud storage cp {f} {gcs_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    for args in EXPORTS:
        run_export(*args)
