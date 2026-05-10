SELECT
    ip AS ip_address,
    country_code,
    country_name,
    region AS region_name,
    city AS city_name
FROM
    {{ source('glamira_raw', 'ip_locations') }}