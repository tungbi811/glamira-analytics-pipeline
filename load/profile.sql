-- Profiling of the BigQuery raw layer (raw.summary, raw.ip_locations, raw.products).
-- Results and what they mean for dbt: docs/profiling/bigquery.md
--
-- Run: paste the whole file into the BigQuery console and click Run.
-- Each statement gets its own result ("View results" per step).
-- Output is counts and formats only, no IPs, emails or other PII values.
-- All raw columns are STRING, so numbers are parsed with SAFE_CAST (NULL when invalid).


-- ============================================================
-- 1. Volume and time range
-- ============================================================

-- 1a. Row counts and duplicate keys (each key should be unique)
SELECT 'summary' AS t, COUNT(*) AS n_rows, COUNT(DISTINCT _id) AS n_keys FROM raw.summary
UNION ALL SELECT 'ip_locations', COUNT(*), COUNT(DISTINCT ip) FROM raw.ip_locations
UNION ALL SELECT 'products', COUNT(*), COUNT(DISTINCT product_id) FROM raw.products;

-- 1b. First / last event, and time_stamp values that aren't whole seconds
SELECT
  TIMESTAMP_SECONDS(MIN(SAFE_CAST(time_stamp AS INT64))) AS first_event,
  TIMESTAMP_SECONDS(MAX(SAFE_CAST(time_stamp AS INT64))) AS last_event,
  COUNTIF(SAFE_CAST(time_stamp AS INT64) IS NULL) AS bad_time_stamp
FROM raw.summary;

-- 1c. Events per day (gaps or spikes = collection problems)
SELECT DATE(TIMESTAMP_SECONDS(SAFE_CAST(time_stamp AS INT64))) AS day, COUNT(*) AS events
FROM raw.summary
GROUP BY day
ORDER BY day;


-- ============================================================
-- 2. Completeness
-- ============================================================

-- 2a. Missing (NULL or '') rate of fields every event should have
SELECT
  COUNT(*) AS n,
  ROUND(100 * COUNTIF(ip IS NULL OR ip = '') / COUNT(*), 2) AS pct_no_ip,
  ROUND(100 * COUNTIF(device_id IS NULL OR device_id = '') / COUNT(*), 2) AS pct_no_device,
  ROUND(100 * COUNTIF(user_id_db IS NULL OR user_id_db = '') / COUNT(*), 2) AS pct_no_user,
  ROUND(100 * COUNTIF(email_address IS NULL OR email_address = '') / COUNT(*), 2) AS pct_no_email,
  ROUND(100 * COUNTIF(store_id IS NULL OR store_id = '') / COUNT(*), 2) AS pct_no_store,
  ROUND(100 * COUNTIF(current_url IS NULL OR current_url = '') / COUNT(*), 2) AS pct_no_url,
  ROUND(100 * COUNTIF(local_time IS NULL OR local_time = '') / COUNT(*), 2) AS pct_no_local_time
FROM raw.summary;

-- 2b. Which fields each event type actually carries
SELECT
  collection,
  COUNT(*) AS n,
  COUNTIF(product_id IS NOT NULL AND product_id != '') AS has_product_id,
  COUNTIF(viewing_product_id IS NOT NULL AND viewing_product_id != '') AS has_viewing_product_id,
  COUNTIF(price IS NOT NULL AND price != '') AS has_price,
  COUNTIF(ARRAY_LENGTH(option) > 0) AS has_option,
  COUNTIF(order_id IS NOT NULL AND order_id != '') AS has_order_id,
  COUNTIF(ARRAY_LENGTH(cart_products) > 0) AS has_cart,
  COUNTIF(key_search IS NOT NULL AND key_search != '') AS has_key_search
FROM raw.summary
GROUP BY collection
ORDER BY n DESC;


-- ============================================================
-- 3. Distinct values
-- ============================================================

-- 3a. How many stores, visitors, users, orders
SELECT
  COUNT(DISTINCT store_id) AS stores,
  COUNT(DISTINCT ip) AS ips,
  COUNT(DISTINCT device_id) AS devices,
  COUNT(DISTINCT NULLIF(user_id_db, '')) AS users,
  COUNT(DISTINCT NULLIF(email_address, '')) AS emails,
  COUNT(DISTINCT order_id) AS orders
FROM raw.summary;

-- 3b. store_id -> website (most common host per store), to build a store lookup in dbt
SELECT store_id, NET.HOST(current_url) AS host, COUNT(*) AS events
FROM raw.summary
GROUP BY store_id, host
QUALIFY ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY events DESC) = 1
ORDER BY events DESC;

-- 3c. Orders: is checkout_success one row per order?
SELECT
  COUNT(*) AS checkout_rows,
  COUNT(DISTINCT order_id) AS orders,
  COUNTIF(order_id IS NULL OR order_id = '') AS no_order_id
FROM raw.summary
WHERE collection = 'checkout_success';


-- ============================================================
-- 4. Join coverage (how well tables match each other)
-- ============================================================

-- 4a. Events whose IP has a location
SELECT
  COUNT(*) AS events,
  ROUND(100 * COUNTIF(l.ip IS NOT NULL) / COUNT(*), 2) AS pct_ip_found,
  ROUND(100 * COUNTIF(l.country_code IS NOT NULL) / COUNT(*), 2) AS pct_with_country
FROM raw.summary AS s
LEFT JOIN raw.ip_locations AS l USING (ip);

-- 4b. Product events whose product was crawled (same 7 events + rule as the crawler)
WITH product_events AS (
  SELECT IF(collection = 'product_view_all_recommend_clicked', viewing_product_id, product_id) AS product_id
  FROM raw.summary
  WHERE collection IN (
    'view_product_detail', 'select_product_option', 'select_product_option_quality',
    'add_to_cart_action', 'product_detail_recommendation_visible',
    'product_detail_recommendation_noticed', 'product_view_all_recommend_clicked')
)
SELECT
  COUNT(*) AS events,
  ROUND(100 * COUNTIF(p.status = 'ok') / COUNT(*), 2) AS pct_ok,
  ROUND(100 * COUNTIF(p.status = 'not_found') / COUNT(*), 2) AS pct_not_found,
  ROUND(100 * COUNTIF(p.product_id IS NULL) / COUNT(*), 2) AS pct_never_crawled
FROM product_events AS e
LEFT JOIN raw.products AS p USING (product_id)
WHERE e.product_id IS NOT NULL AND e.product_id != '';

-- 4c. Ordered items whose product was crawled (cart ids were not in the crawl list)
SELECT
  COUNT(*) AS items,
  COUNT(DISTINCT c.product_id) AS distinct_products,
  ROUND(100 * COUNTIF(p.status = 'ok') / COUNT(*), 2) AS pct_ok,
  ROUND(100 * COUNTIF(p.product_id IS NULL) / COUNT(*), 2) AS pct_never_crawled
FROM raw.summary AS s, UNNEST(s.cart_products) AS c
LEFT JOIN raw.products AS p ON p.product_id = c.product_id
WHERE s.collection = 'checkout_success';


-- ============================================================
-- 5. Formats dbt has to parse
-- ============================================================

-- 5a. Price formats per currency (digits shown as 9), e.g. '9 999,99' vs '9,999.99'
SELECT REGEXP_REPLACE(price, r'\d', '9') AS pattern, currency, COUNT(*) AS n, ANY_VALUE(price) AS example
FROM raw.summary
WHERE price IS NOT NULL AND price != ''
GROUP BY pattern, currency
ORDER BY n DESC
LIMIT 30;

-- 5b. Same for prices inside orders (used for revenue)
SELECT REGEXP_REPLACE(c.price, r'\d', '9') AS pattern, c.currency, COUNT(*) AS n, ANY_VALUE(c.price) AS example
FROM raw.summary AS s, UNNEST(s.cart_products) AS c
WHERE s.collection = 'checkout_success'
GROUP BY pattern, c.currency
ORDER BY n DESC
LIMIT 30;

-- 5c. local_time formats (not zero-padded, e.g. '12:21:4')
SELECT REGEXP_REPLACE(local_time, r'\d', '9') AS pattern, COUNT(*) AS n, ANY_VALUE(local_time) AS example
FROM raw.summary
GROUP BY pattern
ORDER BY n DESC
LIMIT 10;

-- 5d. Option labels. option_id NULL = came from the flat-dict shape
SELECT o.option_label, COUNT(*) AS n, COUNTIF(o.option_id IS NULL) AS from_flat_dict
FROM raw.summary, UNNEST(option) AS o
GROUP BY o.option_label
ORDER BY n DESC
LIMIT 20;

-- 5e. Marketing values (false / text / NULL)
SELECT utm_source, utm_medium, COUNT(*) AS n
FROM raw.summary
GROUP BY utm_source, utm_medium
ORDER BY n DESC
LIMIT 15;

-- 5f. Products: crawl status and parseable prices
SELECT
  status,
  COUNT(*) AS n,
  COUNTIF(SAFE_CAST(price AS NUMERIC) IS NULL) AS bad_price,
  COUNT(DISTINCT product_type) AS product_types,
  COUNTIF(name IS NULL OR name = '') AS no_name
FROM raw.products
GROUP BY status;
