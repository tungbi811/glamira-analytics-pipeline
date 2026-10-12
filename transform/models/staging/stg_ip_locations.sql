SELECT
    ip AS location_ip,
    NULLIF(NULLIF(country_code, '-'), '') AS country_code,
    NULLIF(NULLIF(country, '-'), '')      AS country_name,
    NULLIF(NULLIF(region, '-'), '')       AS region_name,
    NULLIF(NULLIF(city, '-'), '')         AS city_name
FROM {{ source('raw', 'ip_locations') }}