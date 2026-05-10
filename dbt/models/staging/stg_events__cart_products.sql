SELECT DISTINCT
    _id AS event_id,
    store_id,
    order_id,
    cart_item.product_id AS product_id,
    cart_item.amount AS amount,
    cart_item.price AS price,
    cart_item.currency AS currency
FROM
    {{ source('glamira_raw', 'summary') }},
    UNNEST(cart_products) AS cart_item
WHERE
    cart_products IS NOT NULL
    AND ARRAY_LENGTH(cart_products) > 0
