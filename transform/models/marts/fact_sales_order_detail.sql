-- One row per order line (order_id + line_number) from checkout_success.
-- Every dimension key falls back to -1 ('unknown'), so no line is lost in a join.
-- Amounts are USD only; local-currency prices stay in int_order_items for audits.
SELECT
    i.order_id,
    i.line_number,
    CAST(FORMAT_DATE('%Y%m%d', DATE(i.order_time)) AS INT64)   AS date_key,
    COALESCE(p.product_key, -1)                                 AS product_key,
    COALESCE(s.store_key, -1)                                   AS store_key,
    IF(
        ip.location_ip IS NULL,
        -1,
        -- same expression as dim_location.location_key
        FARM_FINGERPRINT(CONCAT(
            COALESCE(ip.country_code, ''), '|', COALESCE(ip.region_name, ''), '|', COALESCE(ip.city_name, '')
        ))
    )                                                           AS location_key,
    COALESCE(c.customer_key, -1)                                AS customer_key,
    IF(
        i.device_type IS NULL,
        -1,
        -- same expression as dim_device.device_key
        FARM_FINGERPRINT(CONCAT(i.device_type, '|', i.os_name, '|', i.browser_name))
    )                                                           AS device_key,
    i.order_time,
    i.order_qty,
    i.unit_price_usd,
    i.line_amount_usd                                           AS sales_amount_usd,
    i.is_free_gift
FROM {{ ref('int_order_items') }} AS i
LEFT JOIN {{ ref('dim_product') }} AS p
    ON i.product_id = p.product_id
LEFT JOIN {{ ref('dim_store') }} AS s
    ON i.store_id = s.store_id
LEFT JOIN {{ ref('stg_ip_locations') }} AS ip
    ON i.ip = ip.location_ip
LEFT JOIN {{ ref('dim_customer') }} AS c
    ON i.device_id = c.device_id
