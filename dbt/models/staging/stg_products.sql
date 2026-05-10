SELECT
    product_id,
    sku AS product_sku,
    product_name,
    product_type,
    type_id AS product_type_id,
    attribute_set AS attribute_set_name,
    price AS base_price,
    min_price,
    max_price,
    gold_weight,
    gender,
    category AS category_id,
    category_name,
    store_code,
    catalog_url
FROM 
    {{ source('glamira_raw', 'product_detail') }}