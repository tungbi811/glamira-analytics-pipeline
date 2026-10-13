-- A table, not a view: the marts read it several times, and as a view each read
-- would re-scan all 41M events.
{{ config(materialized='table') }}

WITH orders AS (
    SELECT *
    FROM {{ ref('stg_events') }}
    WHERE event_name = 'checkout_success'
        AND order_id IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY event_time, event_id) = 1
),

items AS (
    SELECT
        o.order_id,
        line_number + 1                              AS line_number,
        o.event_id,
        o.event_time                                 AS order_time,
        o.local_time,
        o.device_id,
        o.user_id,
        o.ip,
        o.store_id,
        o.resolution,
        -- Order matters: tablets before mobile, and Edge/Samsung/Chrome before Safari
        -- because their user agents also contain 'Safari'.
        CASE
            WHEN REGEXP_CONTAINS(o.user_agent, r'iPad|Tablet') THEN 'tablet'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Android') AND NOT REGEXP_CONTAINS(o.user_agent, r'Mobile') THEN 'tablet'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Mobi|iPhone|iPod|Android') THEN 'mobile'
            WHEN o.user_agent IS NULL THEN NULL
            ELSE 'desktop'
        END                                          AS device_type,
        CASE
            WHEN REGEXP_CONTAINS(o.user_agent, r'iPhone|iPad|iPod') THEN 'iOS'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Android') THEN 'Android'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Windows') THEN 'Windows'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Mac OS X|Macintosh') THEN 'macOS'
            WHEN REGEXP_CONTAINS(o.user_agent, r'CrOS') THEN 'Chrome OS'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Linux') THEN 'Linux'
            WHEN o.user_agent IS NULL THEN NULL
            ELSE 'other'
        END                                          AS os_name,
        CASE
            WHEN REGEXP_CONTAINS(o.user_agent, r'FBAN|FBAV|Instagram') THEN 'Facebook/Instagram app'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Edg/|Edge/|EdgiOS') THEN 'Edge'
            WHEN REGEXP_CONTAINS(o.user_agent, r'SamsungBrowser') THEN 'Samsung Internet'
            WHEN REGEXP_CONTAINS(o.user_agent, r'OPR/|Opera') THEN 'Opera'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Chrome/|CriOS') THEN 'Chrome'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Firefox|FxiOS') THEN 'Firefox'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Safari') THEN 'Safari'
            WHEN REGEXP_CONTAINS(o.user_agent, r'Trident|MSIE') THEN 'Internet Explorer'
            WHEN o.user_agent IS NULL THEN NULL
            ELSE 'other'
        END                                          AS browser_name,
        item.product_id,
        item.option,
        SAFE_CAST(item.amount AS INT64)              AS order_qty,
        {{ parse_price('item.price') }}              AS unit_price,
        NULLIF(item.currency, '')                    AS currency_symbol
    FROM orders AS o,
        UNNEST(o.cart_products) AS item WITH OFFSET AS line_number
)

SELECT
    i.*,
    c.currency_code,
    i.unit_price = 0                                          AS is_free_gift,
    i.order_qty * i.unit_price                                AS line_amount,
    ROUND(i.unit_price / r.units_per_usd, 2)                  AS unit_price_usd,
    ROUND(i.order_qty * i.unit_price / r.units_per_usd, 2)    AS line_amount_usd
FROM items AS i
LEFT JOIN {{ ref('currency') }} AS c
    ON i.store_id = c.store_id
LEFT JOIN {{ ref('exchange_rates') }} AS r
    ON c.currency_code = r.currency_code