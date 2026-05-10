SELECT
    {{ dbt_utils.generate_surrogate_key(['option_id', 'value_id']) }} AS option_key,
    option_id,
    option_label,
    value_id,
    value_label
FROM {{ ref('stg_events__options') }}
GROUP BY 2,3,4,5