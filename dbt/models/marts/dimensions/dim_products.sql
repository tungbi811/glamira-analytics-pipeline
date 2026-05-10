SELECT
    {{ dbt_utils.generate_surrogate_key (["product_id", "product_name"]) }} AS product_key,
    product_id,
    product_sku,
    product_name,
    product_type,
    attribute_set_name,
    base_price,
    min_price,
    max_price,
    gold_weight,
    gender,
    category_id,
    category_name,
    catalog_url
FROM 
    {{ ref('stg_products') }}