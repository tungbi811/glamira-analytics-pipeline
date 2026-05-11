SELECT
    _id AS event_id,
    opt.option_id AS option_id,
    opt.option_label AS option_label,
    opt.value_id AS value_id,
    opt.value_label AS value_label
FROM 
    {{ source('glamira_raw', 'summary') }},
    UNNEST(option) AS opt
WHERE option IS NOT NULL
    AND ARRAY_LENGTH(option) > 0
