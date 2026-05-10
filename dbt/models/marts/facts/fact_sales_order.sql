SELECT
    e.event_id,
    e.order_id,
    cp.product_id,
    e.store_id,
    e.is_paypal,
    cp.price_usd,
    cp.amount,
    date_key,
    customer_key,
    product_key,
    location_key
FROM
    {{ ref('stg_events') }} as e 
LEFT JOIN {{ ref('int_events__cart_products') }} cp
    ON e.event_id = cp.event_id
LEFT JOIN {{ ref('dim_customers') }} c
    ON c.customer_id = e.customer_id
LEFT JOIN {{ ref('dim_date') }} d
    ON DATE(TIMESTAMP_SECONDS(CAST(e.time_stamp AS INT64))) = d.full_date
LEFT JOIN {{ ref('dim_locations') }} l 
    ON l.ip_address = e.ip_address
LEFT JOIN {{ ref('dim_products') }} p
    ON CAST(cp.product_id AS INT64) = p.product_id
WHERE
    e.collection = 'checkout_success'