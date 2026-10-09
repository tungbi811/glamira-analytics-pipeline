#!/bin/bash
PROJECT="project-07d9073d-6ad1-4f38-99e"
DATASET="glamira_raw"

run_query() {
    echo "\n=== $1 ==="
    bq query --nouse_legacy_sql --project_id=${PROJECT} "$2"
}

run_query "Row counts" "
SELECT 'summary'         AS table_name, COUNT(*) AS row_count FROM \`${PROJECT}.${DATASET}.summary\`
UNION ALL
SELECT 'ip_locations',                  COUNT(*)              FROM \`${PROJECT}.${DATASET}.ip_locations\`
UNION ALL
SELECT 'product_details',               COUNT(*)              FROM \`${PROJECT}.${DATASET}.product_details\`
"

run_query "Summary NULL counts" "
SELECT
  COUNTIF(_id        IS NULL) AS null_id,
  COUNTIF(store_id   IS NULL) AS null_store_id,
  COUNTIF(ip         IS NULL) AS null_ip,
  COUNTIF(collection IS NULL) AS null_collection,
  COUNTIF(time_stamp IS NULL) AS null_time_stamp,
  COUNTIF(product_id IS NULL) AS null_product_id
FROM \`${PROJECT}.${DATASET}.summary\`
"

run_query "Summary distinct values" "
SELECT
  COUNT(DISTINCT store_id)   AS distinct_stores,
  COUNT(DISTINCT collection) AS distinct_collections,
  COUNT(DISTINCT ip)         AS distinct_ips,
  COUNT(DISTINCT device_id)  AS distinct_devices
FROM \`${PROJECT}.${DATASET}.summary\`
"

run_query "Event distribution" "
SELECT collection, COUNT(*) AS event_count
FROM \`${PROJECT}.${DATASET}.summary\`
GROUP BY collection
ORDER BY event_count DESC
"

run_query "ip_locations profiling" "
SELECT
  COUNT(*)                      AS total_rows,
  COUNT(DISTINCT ip)            AS distinct_ips,
  COUNT(DISTINCT country_code)  AS distinct_countries,
  COUNTIF(country_code IS NULL) AS null_country
FROM \`${PROJECT}.${DATASET}.ip_locations\`
"

run_query "product_details profiling" "
SELECT
  COUNT(*)                            AS total_rows,
  COUNT(DISTINCT product_id)          AS distinct_products,
  COUNT(DISTINCT category_name)       AS distinct_categories,
  COUNTIF(product_name IS NULL OR product_name = '')  AS missing_name
FROM \`${PROJECT}.${DATASET}.product_details\`
"
