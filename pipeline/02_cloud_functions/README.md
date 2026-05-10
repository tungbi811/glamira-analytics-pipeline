# Cloud Function: GCS → BigQuery

Triggered by new `.jsonl` files in GCS. Loads each file into the matching BigQuery table as it arrives — runs in parallel with `export_to_gcs.py`.

## What it loads

| GCS path | BigQuery table | Schema |
|---|---|---|
| `glamira-data/processed/summary/` | `glamira_raw.summary` | Explicit (all STRING + RECORD) |
| `glamira-data/processed/ip_locations/` | `glamira_raw.ip_locations` | Autodetect |
| `glamira-data/processed/product_details/` | `glamira_raw.product_details` | Autodetect |

The BigQuery dataset `glamira_raw` is created automatically on first invocation.

## Idempotency

The function uses the **filename as a BigQuery job ID**. BigQuery rejects duplicate job IDs, so even if Pub/Sub delivers the same event multiple times (at-least-once delivery), only the first load job succeeds — subsequent attempts are caught as `Already Exists` and skipped safely.

## Deployment (Google Cloud Console)

1. Go to **Cloud Run functions** → **Create function**
2. Configure:
   - Service name: `gcs-to-bigquery-loader`
   - Region: `australia-southeast1`
   - Runtime: `Python 3.12`
3. Add trigger → **Cloud Storage trigger**:
   - Trigger name: `trigger-bigquery-load`
   - Event type: `google.cloud.storage.object.v1.finalized`
   - Bucket: `unigap`
4. Click **Create**, then paste `main.py` and `requirements.txt` into the inline editor
5. Entry point: `trigger_bigquery_load`

## IAM requirements

The function's service account needs:
- `BigQuery Data Editor`
- `BigQuery Job User`

Grant via **IAM → Edit** on the Compute Engine default service account (`252602468432-compute@developer.gserviceaccount.com`).

## Monitoring

Go to **Cloud Run → gcs-to-bigquery-loader → Logs** to see per-file load results.

Log messages:
- `Loading gs://... → ...` — load job started
- `Loaded <file>` — successfully loaded
- `Job ... already completed successfully.` — duplicate event, safely skipped
- `Error: ...` — unexpected failure