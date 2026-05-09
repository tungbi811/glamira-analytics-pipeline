import json
import os
from google.cloud import bigquery

PROJECT   = os.environ.get("GCP_PROJECT", "unigap")
DATASET   = os.environ.get("BQ_DATASET",  "glamira_raw")
SCHEMA_PATH = os.environ.get("SCHEMA_PATH", "raw_events.json")

# Maps GCS path prefix to (BigQuery table, use_schema)
COLLECTION_MAP = {
    "processed/summary/":         ("summary",        True),
    "processed/ip_locations/":    ("ip_locations",   False),
    "processed/product_details/": ("product_details",False),
}


def load_schema(path):
    with open(path) as f:
        return bigquery.schema.SchemaField.from_api_repr_list(json.load(f))


def trigger_bigquery_load(event, context):
    """Cloud Function triggered by a new file in GCS. Appends the file to the matching BigQuery table."""
    file_name = event["name"]
    bucket    = event["bucket"]

    table_id   = None
    use_schema = False

    for prefix, (table, schema) in COLLECTION_MAP.items():
        if file_name.startswith(prefix) and file_name.endswith(".jsonl"):
            table_id   = table
            use_schema = schema
            break

    if not table_id:
        print(f"Skipping {file_name} — no matching collection")
        return

    client     = bigquery.Client()
    table_ref  = f"{PROJECT}.{DATASET}.{table_id}"
    source_uri = f"gs://{bucket}/{file_name}"

    job_config = bigquery.LoadJobConfig(
        source_format      = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition  = bigquery.WriteDisposition.WRITE_APPEND,
        ignore_unknown_values = True,
    )

    if use_schema:
        job_config.schema = load_schema(SCHEMA_PATH)
    else:
        job_config.autodetect = True

    print(f"Loading {source_uri} → {table_ref}")
    job = client.load_table_from_uri(source_uri, table_ref, job_config=job_config)

    try:
        job.result()
        print(f"Done — {job.output_rows:,} rows loaded into {table_ref}")
    except Exception as e:
        print(f"FAILED: {e}")
        raise
