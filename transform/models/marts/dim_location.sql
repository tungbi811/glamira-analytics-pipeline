-- One row per country + region + city, plus an 'unknown' row (location_key -1).
-- location_key hashes the three names; fact_sales_order_detail builds the same key
-- from the order's IP, so the expression must stay identical in both models.
SELECT
    FARM_FINGERPRINT(CONCAT(
        COALESCE(country_code, ''), '|', COALESCE(region_name, ''), '|', COALESCE(city_name, '')
    ))                  AS location_key,
    country_code,
    country_name,
    region_name,
    city_name
FROM {{ ref('stg_ip_locations') }}
GROUP BY country_code, country_name, region_name, city_name

UNION ALL

SELECT
    -1          AS location_key,
    NULL        AS country_code,
    'Unknown'   AS country_name,
    NULL        AS region_name,
    NULL        AS city_name
