-- One row per product_id, plus an 'unknown' row (product_key -1) for order lines
-- whose product was never crawled (mostly free-gift pendants).
SELECT
    FARM_FINGERPRINT(product_id) AS product_key,
    product_id,
    product_name,
    sku,
    product_type,
    type_id,
    attribute_set,
    collection_id,
    collection_name,
    category_id,
    category_name,
    gender,
    price,
    min_price,
    max_price,
    store_code,
    crawl_status,
    is_page_found,
    crawled_time
FROM {{ ref('stg_products') }}

UNION ALL

SELECT
    -1          AS product_key,
    'unknown'   AS product_id,
    'Unknown'   AS product_name,
    NULL        AS sku,
    NULL        AS product_type,
    NULL        AS type_id,
    NULL        AS attribute_set,
    NULL        AS collection_id,
    NULL        AS collection_name,
    NULL        AS category_id,
    NULL        AS category_name,
    NULL        AS gender,
    NULL        AS price,
    NULL        AS min_price,
    NULL        AS max_price,
    NULL        AS store_code,
    'not_crawled' AS crawl_status,
    FALSE       AS is_page_found,
    NULL        AS crawled_time
