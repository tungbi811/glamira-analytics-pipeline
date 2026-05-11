# Testing & Monitoring

End-to-end pipeline validation and data profiling for the Glamira analytics pipeline.

## Checklist

### Pipeline validation
- [x] `export_to_gcs.py` completes with 0 upload failures
- [x] Cloud Function triggers on each `.jsonl` upload
- [x] All 3 BigQuery tables exist with correct row counts

See [docs/data_profiling.md](../../docs/data_profiling.md) for row counts and profiling results.

## Monitoring

Cloud Function logs: **Cloud Run → gcs-to-bigquery-loader → Logs**

Check for failed loads:
```
severity=ERROR
```
