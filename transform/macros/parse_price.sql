{% macro parse_price(column) %}
{%- set cleaned -%}
REGEXP_REPLACE(REPLACE({{ column }}, '٫', '.'), r'[^0-9.,]', '')
{%- endset -%}
-- Locale prices like '1.356,00', '1,069.00', '7 423,00', '61٫00' (Arabic decimal sign).
-- The last '.' or ',' followed by exactly 2 digits is the decimal separator.
CASE
    WHEN REGEXP_CONTAINS({{ cleaned }}, r'[.,][0-9]{2}$') THEN
        SAFE_CAST(
            CONCAT(
                REGEXP_REPLACE(REGEXP_EXTRACT({{ cleaned }}, r'^(.*)[.,][0-9]{2}$'), r'[.,]', ''),
                '.',
                RIGHT({{ cleaned }}, 2)
            ) AS NUMERIC
        )
    ELSE SAFE_CAST(REGEXP_REPLACE({{ cleaned }}, r'[.,]', '') AS NUMERIC)
END
{% endmacro %}
