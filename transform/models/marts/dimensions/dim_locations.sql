SELECT
    {{ dbt_utils.generate_surrogate_key(["ip_address"]) }} AS location_key,
    ip_address,
    country_code,
    country_name,
    region_name,
    city_name
FROM
    {{ ref('stg_locations') }}
GROUP BY 2,3,4,5,6