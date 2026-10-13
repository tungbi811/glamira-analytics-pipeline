-- One row per device type + OS + browser seen on orders, plus an 'unknown' row (device_key -1).
-- device_key hashes the three names; fact_sales_order_detail builds the same key,
-- so the expression must stay identical in both models.
SELECT
    FARM_FINGERPRINT(CONCAT(device_type, '|', os_name, '|', browser_name)) AS device_key,
    device_type,
    os_name,
    browser_name
FROM {{ ref('int_order_items') }}
WHERE device_type IS NOT NULL
GROUP BY device_type, os_name, browser_name

UNION ALL

SELECT
    -1          AS device_key,
    'unknown'   AS device_type,
    NULL        AS os_name,
    NULL        AS browser_name
