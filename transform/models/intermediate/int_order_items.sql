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