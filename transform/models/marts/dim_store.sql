-- One row per store (website), plus an 'unknown' row (store_key -1).
-- Test stores on glamira.local are not in the seed, so they map to -1.
WITH stores AS (
    SELECT
        store_id,
        store_host,
        currency_code,
        LOWER(ARRAY_REVERSE(SPLIT(store_host, '.'))[OFFSET(0)]) AS top_level_domain
    FROM {{ ref('currency') }}
)

SELECT
    FARM_FINGERPRINT(store_id)                                AS store_key,
    store_id,
    REPLACE(store_host, 'www.', '')                           AS store_name,
    store_host,
    IF(store_id = '1', 'Ring-Paare', 'Glamira')               AS brand_name,
    CASE
        WHEN top_level_domain IN ('com', 'africa', 'store') THEN NULL
        WHEN top_level_domain = 'uk' THEN 'GB'
        ELSE UPPER(top_level_domain)
    END                                                       AS country_code,
    currency_code
FROM stores

UNION ALL

SELECT
    -1          AS store_key,
    'unknown'   AS store_id,
    'Unknown'   AS store_name,
    NULL        AS store_host,
    NULL        AS brand_name,
    NULL        AS country_code,
    NULL        AS currency_code
