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
