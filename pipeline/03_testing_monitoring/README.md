# Testing & Monitoring

End-to-end pipeline validation and data profiling for the Glamira analytics pipeline.

## Checklist

### Pipeline validation
- [ ] `export_to_gcs.py` completes with 0 upload failures
- [ ] Cloud Function triggers on each `.jsonl` upload
- [ ] All 3 BigQuery tables exist with correct row counts

### Expected row counts
| BigQuery table | Source collection | Expected rows |
|---|---|---|
| `glamira_raw.summary` | `summary` | ~41,400,000 |
| `glamira_raw.ip_locations` | `ip_locations` | ~3,239,628 |
| `glamira_raw.product_details` | `product_details` | ~18,987 |

### Data profiling
Run in BigQuery console to validate each table:

**Row counts**
```sql
SELECT COUNT(*) FROM `project-07d9073d-6ad1-4f38-99e.glamira_raw.summary`;
SELECT COUNT(*) FROM `project-07d9073d-6ad1-4f38-99e.glamira_raw.ip_locations`;
SELECT COUNT(*) FROM `project-07d9073d-6ad1-4f38-99e.glamira_raw.product_details`;
```

**NULL counts (summary)**
```sql
SELECT
  COUNTIF(_id           IS NULL) AS null_id,
  COUNTIF(store_id      IS NULL) AS null_store_id,
  COUNTIF(ip            IS NULL) AS null_ip,
  COUNTIF(collection    IS NULL) AS null_collection,
  COUNTIF(time_stamp    IS NULL) AS null_time_stamp,
  COUNTIF(product_id    IS NULL) AS null_product_id
FROM `project-07d9073d-6ad1-4f38-99e.glamira_raw.summary`;
```

**Distinct values (summary)**
```sql
SELECT
  COUNT(DISTINCT store_id)   AS distinct_stores,
  COUNT(DISTINCT collection) AS distinct_collections,
  COUNT(DISTINCT ip)         AS distinct_ips,
  COUNT(DISTINCT device_id)  AS distinct_devices
FROM `project-07d9073d-6ad1-4f38-99e.glamira_raw.summary`;
```

**Event distribution**
```sql
SELECT collection, COUNT(*) AS event_count
FROM `project-07d9073d-6ad1-4f38-99e.glamira_raw.summary`
GROUP BY collection
ORDER BY event_count DESC;
```

**Data type consistency check (option field)**
```sql
SELECT
  ARRAY_LENGTH(option) AS option_length,
  COUNT(*) AS cnt
FROM `project-07d9073d-6ad1-4f38-99e.glamira_raw.summary`
GROUP BY option_length
ORDER BY option_length;
```

**ip_locations profiling**
```sql
SELECT
  COUNT(*)                      AS total_rows,
  COUNT(DISTINCT ip)            AS distinct_ips,
  COUNT(DISTINCT country_code)  AS distinct_countries,
  COUNTIF(country_code IS NULL) AS null_country
FROM `project-07d9073d-6ad1-4f38-99e.glamira_raw.ip_locations`;
```

**product_details profiling**
```sql
SELECT
  COUNT(*)                       AS total_rows,
  COUNT(DISTINCT product_id)     AS distinct_products,
  COUNT(DISTINCT category_name)  AS distinct_categories,
  COUNTIF(name IS NULL OR name = '') AS missing_name
FROM `project-07d9073d-6ad1-4f38-99e.glamira_raw.product_details`;
```

## Monitoring

Cloud Function logs: **Cloud Run → gcs-to-bigquery-loader → Logs**

Check for failed loads:
```
severity=ERROR
```
