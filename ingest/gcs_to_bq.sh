#!/usr/bin/env bash
# Load the newest complete export of each table from GCS into BigQuery `raw`.
#
# A run is complete when its folder has _SUCCESS (written last by mongo_to_gcs.py).
# --replace overwrites the table, so re-running never duplicates rows.
#
# Usage (from the repo root, on the VM or the Mac):
#   bash ingest/gcs_to_bq.sh                 # all tables
#   bash ingest/gcs_to_bq.sh products        # one table

set -euo pipefail  # stop on the first error

# GCS_BUCKET comes from .env, e.g. gs://glamira-analytics-511114-raw
set -a && . ./.env && set +a
EXPORT="$GCS_BUCKET/export"
TABLES="${*:-summary ip_locations products}"

for TABLE in $TABLES; do
  # Newest folder that has _SUCCESS. Run ids are UTC timestamps, so sort = by time.
  RUN=$(gcloud storage ls "$EXPORT/$TABLE/*/_SUCCESS" | sort | tail -1 | xargs dirname)
  echo "Loading raw.$TABLE from $RUN"

  # --parquet_enable_list_inference: option / cart_products load as nested lists
  bq load --source_format=PARQUET --parquet_enable_list_inference --replace \
    "raw.$TABLE" "$RUN/part-*.parquet"
done

# Compare these with the "rows" in each _SUCCESS file.
bq query --use_legacy_sql=false 'SELECT table_id, row_count FROM raw.__TABLES__ ORDER BY table_id'
