# Problems Encountered

## Ingestion

### 1. mongosh connects to localhost by default
**Symptom**: `MongoNetworkError: connect ECONNREFUSED 127.0.0.1:27017`  
**Cause**: Running `mongosh script.js` without a URI defaults to `localhost:27017`.  
**Fix**: Pass the URI explicitly — `mongosh "mongodb://${VM_EXTERNAL_IP}:27017/countly" script.js`. Consolidated into a single `ingestion/mongo.sh` wrapper that sources `.env` and passes the URI automatically.

### 2. $addToSet used too much memory
**Symptom**: `MongoServerError: $addToSet used too much memory`  
**Cause**: `$addToSet: "$fields.v"` on 41M documents exceeded MongoDB's 100MB aggregation memory limit.  
**Fix**: Removed `unique_values` / `unique_count` fields from the aggregation. Replaced with `not_null_count` which doesn't accumulate values in memory.

### 3. export_to_gcs.py could not find config.py
**Symptom**: `ModuleNotFoundError: No module named 'config'`  
**Cause**: `sys.path.insert` was pointing to the wrong directory — `pipeline/` had no `config.py`.  
**Fix**: Created an independent `pipeline/config.py` so the relative `..` path resolves correctly from `pipeline/01_mongo_to_gcs/`.

---

## Cloud Function (GCS → BigQuery)

### 4. Wrong entry point name
**Symptom**: "The specified function (entry point) might not be present in your source code"  
**Cause**: The entry point field in Cloud Run console must match the exact function name in `main.py`.  
**Fix**: Set entry point to `trigger_bigquery_load`.

### 5. KeyError: 'bucket'
**Symptom**: `KeyError: 'bucket'` in Cloud Function logs  
**Cause**: Trigger was set to `google.cloud.audit.log.v1.written` (Cloud Audit Log), which wraps the GCS event in a `protoPayload` structure instead of exposing `bucket` and `name` directly.  
**Fix**: Switch trigger to `google.cloud.storage.object.v1.finalized` (direct GCS event).

### 6. 429 Rate limit exceeded
**Symptom**: `TooManyRequests: 429 Exceeded rate limits: too many table update operations for this table`  
**Cause**: Direct GCS trigger fires all invocations simultaneously when many files are uploaded quickly. BigQuery allows max 5 table update operations per 10 seconds per table.  
**Failed attempts**:
- Setting max instances to 1 — did not fully resolve, trigger still queued invocations faster than BigQuery could process
- Switching to Cloud Audit Log trigger — natural delivery delay helped but caused `KeyError: 'bucket'` (problem #5)
- Adding exponential backoff retry loop without job ID — caused more duplicate loads when combined with Pub/Sub retries  

**Fix**: First apply the filename-based job ID (problem #7). Once idempotent, add an internal retry loop only for 429 errors — retrying the same job ID is safe because BigQuery will either complete it or return `Already Exists`. Retries for all other errors are skipped since they are permanent failures (schema mismatch, permission denied, etc.) that won't succeed on retry.

```python
for attempt in range(4):
    try:
        job = client.load_table_from_uri(source_uri, table_ref, job_config=job_config, job_id=job_id)
        job.result()
        return
    except Exception as e:
        if "Already Exists" in str(e):
            return
        if "429" in str(e) and attempt < 3:
            wait = 15 * (2 ** attempt)  # 15s, 30s, 60s
            time.sleep(wait)
        else:
            raise e
```

### 7. Same file loaded multiple times (8–9x) ✓ Resolved
**Symptom**: One uploaded file triggered 8–9 function invocations, each successfully loading the same data.  
**Cause**: Eventarc uses Pub/Sub internally (at-least-once delivery). Pub/Sub sends the same message multiple times if it doesn't receive an acknowledgement within the deadline. Even when the function returns HTTP 200, the ack can be lost or delayed due to network issues, causing redelivery.  
**Failed attempts**:
- Replacing `raise` with `return` — function returns 200 but Pub/Sub still redelivers
- Setting max instances to 1 — serializes execution but doesn't prevent duplicate events
- Purging Pub/Sub backlog with `gcloud pubsub subscriptions seek --time=now` — clears existing backlog but doesn't prevent future duplicates
- Adding `loaded_files` tracking table — correct approach but rejected for complexity  

**Fix**: Use the filename as a **BigQuery job ID** (`job_id=job_id`). BigQuery guarantees that two load jobs with the same ID cannot both succeed — the second attempt raises `Already Exists` which is caught and skipped. This makes the function fully idempotent regardless of how many times Pub/Sub delivers the event.

```python
job_id = f"load_{file_name.replace('/', '_').replace('.', '_')}"
job = client.load_table_from_uri(source_uri, table_ref, job_config=job_config, job_id=job_id)
```

### 8. Cloud Function keeps running after export finishes
**Symptom**: Function continues inserting data after `export_to_gcs.py` completes.  
**Cause**: Eventarc/Pub/Sub queues undelivered events and keeps retrying them indefinitely, even after the export has stopped.  
**Fix**: Delete the Cloud Function or set max instances to 0 to immediately stop all invocations. With the job ID fix (problem #7), redelivered events are safely skipped so this is no longer a data integrity issue.

---

## Code Review Findings (2026-05-11)

Issues identified during code review. Items marked ✓ are fixed.

### 9. Hardcoded GCP project ID ✓ Resolved
**File**: `load/02_cloud_functions/main.py`  
**Cause**: `PROJECT` and `DATASET` were hardcoded strings; project ID value was also malformed (truncated UUID).  
**Fix**: Replaced with `os.environ["GCP_PROJECT"]` and `os.environ.get("BQ_DATASET", "glamira_raw")`. Values now live in `.env` and must be set as Cloud Function runtime env vars at deploy time.

### 10. Non-idempotent Mongo export resume
**File**: `load/01_mongo_to_gcs/export_to_gcs.py:139-176`  
**Cause**: Resume logic uses `cursor.skip(completed_batches * BATCH_SIZE)` on a `find()` with no `.sort()`. MongoDB cursors without an explicit sort have no stable order — resuming after a partial run can silently skip or duplicate documents. `.skip()` is also O(N) server-side.  
**Fix**: Add `.sort("_id", 1)` and resume using the last seen `_id` with a range filter (`{"_id": {"$gt": last_id}}`).

### 11. TLS verification disabled globally
**File**: `ingest/03_product_crawler/crawl_product_details.py:89`  
**Cause**: `verify=False` passed to every request, not just specific regional domains as the comment implies. Exposes all crawl traffic to MITM and silently masks certificate errors.  
**Fix**: Remove `verify=False` or pin per-domain if a specific cert issue exists.

### 12. `dim_locations` duplicate surrogate key
**File**: `transform/models/marts/dimensions/dim_locations.sql`  
**Cause**: Surrogate key is built from `ip_address` only, but `GROUP BY` includes 5 columns. Any IP that appears with varying country/city values produces duplicate `location_key` rows, causing fan-out in `fact_sales_order`.  
**Fix**: Either group only on `ip_address` (pick one row with `QUALIFY ROW_NUMBER() = 1`) or build the surrogate key from all five columns.

### 13. `dim_customers` duplicate key on multi-email customers
**File**: `transform/models/marts/dimensions/dim_customers.sql`  
**Cause**: `GROUP BY customer_id, email_address` creates one row per (customer_id, email) pair. A customer with two recorded emails produces duplicate `customer_key` values. `fact_sales_order` joins on `customer_id` and fans out.  
**Fix**: Deduplicate to one row per `customer_id` (e.g., pick the most recent email with `QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY ...) = 1`).

### 14. `dim_products` unaggregated + cross-type JOIN
**File**: `transform/models/marts/dimensions/dim_products.sql`, `transform/models/marts/facts/fact_sales_order.sql:24`  
**Cause**: `dim_products` has no DISTINCT/aggregation — any duplicate `product_id` in the source fans out the fact. The join uses `CAST(cp.product_id AS INT64) = p.product_id`, silently dropping non-numeric product IDs.  
**Fix**: Add `QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY ...) = 1` to `dim_products`. Keep `product_id` as STRING throughout and join on STRING.

### 15. Zero dbt tests and no source freshness
**Files**: `transform/models/staging/sources.yml`, all model directories  
**Cause**: No `schema.yml` files exist for any models, and `sources.yml` has no `loaded_at_field` or `freshness` config. Duplicate keys and broken joins (issues #12–14) would be caught immediately by basic `unique` + `not_null` tests.  
**Fix**: Add `schema.yml` to each model layer with at minimum `unique` + `not_null` tests on every surrogate key and `event_id`. Add `loaded_at_field: time_stamp` and `freshness` thresholds to `sources.yml`.

### 16. `time_stamp` cast repeated across models
**Files**: `load/02_cloud_functions/main.py:25`, `dim_date.sql`, `fact_sales_order.sql`  
**Cause**: `time_stamp` is stored as STRING in BigQuery and cast to INT64/TIMESTAMP in every consuming model.  
**Fix**: Cast once in `stg_events` as `TIMESTAMP_SECONDS(CAST(time_stamp AS INT64)) AS event_at` and use `event_at` everywhere downstream.

### 17. No partitioning or clustering on `fact_sales_order`
**File**: `transform/dbt_project.yml:26-32`  
**Cause**: 41M-row fact table is materialized as a plain table with no `partition_by` or `cluster_by`, making every query a full scan.  
**Fix**: Add `partition_by={"field": "event_date", "data_type": "date"}` and `cluster_by=["customer_key", "product_key"]` to the model config.

### 18. `stg_events` rescanned on every mart build ✓ Resolved
**File**: `transform/models/staging/stg_events.sql`  
**Cause**: Staging layer defaulted to `view`; every downstream mart re-ran the full 41M-row source scan.  
**Fix**: Added `{{ config(materialized='table') }}` to `stg_events.sql` so the source is scanned once.

### 19. `lookup_ip_locations.py` drops output collection on every run
**File**: `ingest/02_ip_geolocation/lookup_ip_locations.py:23`  
**Cause**: `out_col.drop()` runs unconditionally, destroying all data if the script is rerun or interrupted.  
**Fix**: Remove the drop and use upserts keyed by `ip` (`update_one({"ip": doc["ip"]}, {"$set": doc}, upsert=True)`).

### 20. Shell-out to `gcloud storage` instead of Python SDK
**File**: `load/01_mongo_to_gcs/export_to_gcs.py:117,165`  
**Cause**: Uses `subprocess` to call the `gcloud` CLI for GCS uploads, which requires the CLI to be installed and authenticated on the host, and makes error handling harder.  
**Fix**: Replace with `google-cloud-storage` Python client (`storage.Client().bucket(...).blob(...).upload_from_filename(...)`).

### 21. `dim_date` derived from event timestamps only
**File**: `transform/models/marts/dimensions/dim_date.sql`  
**Cause**: Date spine is built from the range of `event_at` values in the data. Any gap in events produces a gap in the date dimension, breaking date-range queries.  
**Fix**: Use `GENERATE_DATE_ARRAY(DATE '2020-01-01', CURRENT_DATE())` to produce a complete, stable date spine.
