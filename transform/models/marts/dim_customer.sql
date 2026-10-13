-- One row per device that placed an order, plus an 'unknown' row (customer_key -1).
-- device_id is the customer because 95% of visitors never log in.
-- Email stays in staging only, to keep PII out of the marts.
SELECT
    FARM_FINGERPRINT(device_id)                                                  AS customer_key,
    device_id,
    ARRAY_AGG(user_id IGNORE NULLS ORDER BY order_time DESC LIMIT 1)[SAFE_OFFSET(0)] AS user_id,
    LOGICAL_OR(user_id IS NOT NULL)                                              AS is_registered,
    MIN(order_time)                                                              AS first_order_time,
    COUNT(DISTINCT order_id)                                                     AS order_count
FROM {{ ref('int_order_items') }}
WHERE device_id IS NOT NULL
GROUP BY device_id

UNION ALL

SELECT
    -1          AS customer_key,
    'unknown'   AS device_id,
    NULL        AS user_id,
    FALSE       AS is_registered,
    NULL        AS first_order_time,
    0           AS order_count
