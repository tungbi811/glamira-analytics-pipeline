WITH
    event_dates AS (
        SELECT DISTINCT
            DATE(TIMESTAMP_SECONDS(CAST(time_stamp AS INT64))) AS full_date
        FROM
            {{ ref('stg_events') }}
    )

SELECT
    CAST(FORMAT_DATE('%Y%m%d', full_date) AS INT64) AS date_key,
    full_date,
    EXTRACT(YEAR FROM full_date) AS year,
    EXTRACT(QUARTER FROM full_date) AS quarter,
    EXTRACT(MONTH FROM full_date) AS month,
    FORMAT_DATETIME('%B', full_date) AS month_name,
    EXTRACT(WEEK FROM full_date) AS week_of_year,
    EXTRACT(DAY FROM full_date) AS day_of_month,
    EXTRACT(DAYOFWEEK FROM full_date) AS day_of_week,
    FORMAT_DATETIME('%A', full_date) AS day_name
FROM 
    event_dates