WITH normalized_prices AS (
    SELECT
        event_id,
        store_id,
        order_id,
        product_id,
        amount,
        price,
        c.currency,
        -- Normalize price once (handle multiple formats)
        CASE
            -- Format: 1,234.56 (comma for thousands, period for decimal)
            WHEN REGEXP_CONTAINS(price, r'^\d{1,3}(,\d{3})*\.\d{2}$')
                THEN SAFE_CAST(REPLACE(price, ',', '') AS FLOAT64)
            -- Format: 1.234,56 (period for thousands, comma for decimal - European)
            WHEN REGEXP_CONTAINS(price, r'^\d{1,3}(\.\d{3})*,\d{2}$')
                THEN SAFE_CAST(REPLACE(REPLACE(price, '.', ''), ',', '.') AS FLOAT64)
            -- Format: 1234.56 (already correct)
            WHEN REGEXP_CONTAINS(price, r'^\d+\.\d{2}$')
                THEN SAFE_CAST(price AS FLOAT64)
            -- Format: 1234,56 (comma as decimal)
            WHEN REGEXP_CONTAINS(price, r'^\d+,\d{2}$')
                THEN SAFE_CAST(REPLACE(price, ',', '.') AS FLOAT64)
            -- Fallback: remove all non-numeric and convert
            ELSE SAFE_CAST(REGEXP_REPLACE(price, r'[^0-9.]', '') AS FLOAT64)
        END as price_numeric
    FROM {{ ref('stg_events__cart_products') }} c
)

SELECT
    event_id,
    store_id,
    order_id,
    product_id,
    amount,
    price_numeric * COALESCE(ex.rate_to_usd, 1) as price_usd
FROM normalized_prices n
LEFT JOIN {{ ref('exchange_rate') }} AS ex
    ON ex.currency = n.currency


