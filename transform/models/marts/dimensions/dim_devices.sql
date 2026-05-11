SELECT
    {{ dbt_utils.generate_surrogate_key(["device_id", "user_agent", "resolution"]) }} AS device_key,
    device_id,
    user_agent,
    resolution
FROM
    {{ ref('stg_events') }}
GROUP BY 2,3,4