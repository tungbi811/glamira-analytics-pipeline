SELECT
    {{ dbt_utils.generate_surrogate_key(['customer_id', 'email_address']) }} AS customer_key,
    customer_id,
    email_address,
    MIN(time_stamp) AS first_seen_at,
    MAX(time_stamp) AS last_seen_at
FROM
    {{ ref('stg_events') }}
GROUP BY 2,3