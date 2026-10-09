import os
import time
import functions_framework
from google.cloud import bigquery

PROJECT = os.environ["GCP_PROJECT"]
DATASET = os.environ.get("BQ_DATASET", "glamira_raw")

# Maps GCS path prefix to (BigQuery table, use_schema)
COLLECTION_MAP = {
    "glamira-data/processed/summary/":         ("summary",        True),
    "glamira-data/processed/ip_locations/":    ("ip_locations",   False),
    "glamira-data/processed/product_details/": ("product_details",False),
}

# Embedded schema for summary table — avoids needing to upload raw_events.json alongside the function
SUMMARY_SCHEMA = [
    bigquery.SchemaField("_id",                             "STRING"),
    bigquery.SchemaField("store_id",                        "STRING"),
    bigquery.SchemaField("referrer_url",                    "STRING"),
    bigquery.SchemaField("user_id_db",                      "STRING"),
    bigquery.SchemaField("resolution",                      "STRING"),
    bigquery.SchemaField("ip",                              "STRING"),
    bigquery.SchemaField("user_agent",                      "STRING"),
    bigquery.SchemaField("device_id",                       "STRING"),
    bigquery.SchemaField("time_stamp",                      "STRING"),
    bigquery.SchemaField("local_time",                      "STRING"),
    bigquery.SchemaField("current_url",                     "STRING"),
    bigquery.SchemaField("api_version",                     "STRING"),
    bigquery.SchemaField("collection",                      "STRING"),
    bigquery.SchemaField("email_address",                   "STRING"),
    bigquery.SchemaField("show_recommendation",             "STRING"),
    bigquery.SchemaField("product_id",                      "STRING"),
    bigquery.SchemaField("collect_id",                      "STRING"),
    bigquery.SchemaField("cat_id",                          "STRING"),
    bigquery.SchemaField("recommendation",                  "STRING"),
    bigquery.SchemaField("utm_medium",                      "STRING"),
    bigquery.SchemaField("utm_source",                      "STRING"),
    bigquery.SchemaField("viewing_product_id",              "STRING"),
    bigquery.SchemaField("recommendation_product_id",       "STRING"),
    bigquery.SchemaField("key_search",                      "STRING"),
    bigquery.SchemaField("recommendation_clicked_position", "STRING"),
    bigquery.SchemaField("currency",                        "STRING"),
    bigquery.SchemaField("is_paypal",                       "STRING"),
    bigquery.SchemaField("price",                           "STRING"),
    bigquery.SchemaField("order_id",                        "STRING"),
    bigquery.SchemaField("recommendation_product_position", "STRING"),
    bigquery.SchemaField("option", "RECORD", mode="REPEATED", fields=[
        bigquery.SchemaField("option_label", "STRING"),
        bigquery.SchemaField("option_id",    "STRING"),
        bigquery.SchemaField("value_label",  "STRING"),
        bigquery.SchemaField("value_id",     "STRING"),
    ]),
    bigquery.SchemaField("cart_products", "RECORD", mode="REPEATED", fields=[
        bigquery.SchemaField("product_id", "STRING"),
        bigquery.SchemaField("amount",     "STRING"),
        bigquery.SchemaField("currency",   "STRING"),
        bigquery.SchemaField("price",      "STRING"),
        bigquery.SchemaField("option", "RECORD", mode="REPEATED", fields=[
            bigquery.SchemaField("option_label", "STRING"),
            bigquery.SchemaField("option_id",    "STRING"),
            bigquery.SchemaField("value_label",  "STRING"),
            bigquery.SchemaField("value_id",     "STRING"),
        ]),
    ]),
]


@functions_framework.cloud_event
def trigger_bigquery_load(cloud_event):
    data = cloud_event.data
    
    # Use standard GCS event data
    bucket = data["bucket"]
    file_name = data["name"]

    table_id = None
    use_schema = False

    for prefix, (table, schema) in COLLECTION_MAP.items():
        if file_name.startswith(prefix) and file_name.endswith(".jsonl"):
            table_id = table
            use_schema = schema
            break

    if not table_id:
        return

    client = bigquery.Client()
    dataset = bigquery.Dataset(f"{PROJECT}.{DATASET}")
    dataset.location = os.environ.get("BQ_LOCATION", "australia-southeast1")
    client.create_dataset(dataset, exists_ok=True)

    table_ref = f"{PROJECT}.{DATASET}.{table_id}"
    source_uri = f"gs://{bucket}/{file_name}"

    # FIX: Use the filename (sanitized) as the Job ID. 
    # If the function retries, BigQuery will see the Job ID already exists and won't insert twice.
    job_id = f"load_{file_name.replace('/', '_').replace('.', '_')}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        ignore_unknown_values=True,
        schema=SUMMARY_SCHEMA if use_schema else None,
        autodetect=False if use_schema else True
    )

    for attempt in range(4):
        try:
            job = client.load_table_from_uri(source_uri, table_ref, job_config=job_config, job_id=job_id)
            job.result()
            print(f"Loaded {file_name}")
            return
        except Exception as e:
            if "Already Exists" in str(e):
                print(f"Job {job_id} already completed successfully.")
                return
            if "429" in str(e) and attempt < 3:
                wait = 15 * (2 ** attempt)  # 15s, 30s, 60s
                print(f"Rate limited, retrying in {wait}s (attempt {attempt + 1}/3)")
                time.sleep(wait)
            else:
                print(f"Error: {e}")
                raise e