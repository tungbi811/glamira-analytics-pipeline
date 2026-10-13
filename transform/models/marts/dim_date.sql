-- One row per day from 2015 to 2035. The data covers 2020-04-01 to 2020-06-04;
-- a wide fixed range means new data never falls outside it (about 7,700 rows).
SELECT
    CAST(FORMAT_DATE('%Y%m%d', d) AS INT64)   AS date_key,
    d                                         AS full_date,
    EXTRACT(YEAR FROM d)                      AS year_number,
    EXTRACT(QUARTER FROM d)                   AS quarter_number,
    EXTRACT(MONTH FROM d)                     AS month_number,
    FORMAT_DATE('%B', d)                      AS month_name,
    EXTRACT(ISOWEEK FROM d)                   AS week_number,
    EXTRACT(DAY FROM d)                       AS day_of_month,
    MOD(EXTRACT(DAYOFWEEK FROM d) + 5, 7) + 1 AS day_of_week,
    FORMAT_DATE('%A', d)                      AS day_name,
    EXTRACT(DAYOFWEEK FROM d) IN (1, 7)       AS is_weekend
FROM UNNEST(GENERATE_DATE_ARRAY('2015-01-01', '2035-12-31')) AS d
