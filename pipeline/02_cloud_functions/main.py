import functions_framework
from google.cloud import bigquery

PROJECT = "project-07d9073d-6ad1-4f38-99e"
DATASET = "glamira_raw"

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
    """Cloud Run function triggered by a new file in GCS. Appends the file to the matching BigQuery table."""
    data      = cloud_event.data
    bucket    = data["bucket"]
    file_name = data["name"]

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

    client = bigquery.Client()
    client.create_dataset(f"{PROJECT}.{DATASET}", exists_ok=True)

    table_ref  = f"{PROJECT}.{DATASET}.{table_id}"
    source_uri = f"gs://{bucket}/{file_name}"

    job_config = bigquery.LoadJobConfig(
        source_format         = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition     = bigquery.WriteDisposition.WRITE_APPEND,
        ignore_unknown_values = True,
    )

    if use_schema:
        job_config.schema = SUMMARY_SCHEMA
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