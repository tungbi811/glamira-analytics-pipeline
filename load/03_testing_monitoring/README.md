# Testing & Monitoring

End-to-end pipeline validation and data profiling for the Glamira analytics pipeline.

## Checklist

### Pipeline validation
- [x] `export_to_gcs.py` completes with 0 upload failures
- [x] Cloud Function triggers on each `.jsonl` upload
- [x] All 3 BigQuery tables exist with correct row counts

### Actual row counts (verified 2026-05-11)
| BigQuery table | Source collection | Expected rows | Actual rows |
|---|---|---|---|
| `glamira_raw.summary` | `summary` | ~41,400,000 | 41,432,473 |
| `glamira_raw.ip_locations` | `ip_locations` | ~3,239,628 | 3,239,628 |
| `glamira_raw.product_details` | `product_details` | ~18,987 | 18,987 |

### Data profiling results (verified 2026-05-11)

**Summary NULL counts**

| null_id | null_store_id | null_ip | null_collection | null_time_stamp | null_product_id |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 19,189,753 |

`product_id` is null for ~46% of events — expected, as most event types (page views, recommendations) are not product-specific.

**Summary distinct values**

| distinct_stores | distinct_collections | distinct_ips | distinct_devices |
|---|---|---|---|
| 86 | 27 | 3,239,628 | 7,691,556 |

**Event distribution**

| collection | event_count |
|---|---|
| view_listing_page | 11,259,694 |
| view_product_detail | 10,944,427 |
| select_product_option | 8,844,342 |
| select_product_option_quality | 2,231,825 |
| view_static_page | 1,451,565 |
| view_landing_page | 1,434,230 |
| product_detail_recommendation_visible | 1,302,362 |
| view_home_page | 1,053,420 |
| listing_page_recommendation_visible | 718,048 |
| product_detail_recommendation_noticed | 490,780 |
| view_shopping_cart | 343,077 |
| landing_page_recommendation_visible | 314,999 |
| search_box_action | 238,308 |
| add_to_cart_action | 187,901 |
| product_detail_recommendation_clicked | 179,228 |
| view_my_account | 112,066 |
| checkout | 88,540 |
| landing_page_recommendation_noticed | 58,186 |
| listing_page_recommendation_noticed | 39,819 |
| view_all_recommend | 33,664 |
| checkout_success | 26,079 |
| listing_page_recommendation_clicked | 25,545 |
| landing_page_recommendation_clicked | 20,128 |
| product_view_all_recommend_clicked | 16,682 |
| view_sorting_relevance | 15,284 |
| sorting_relevance_click_action | 1,713 |
| back_to_product_action | 561 |

**ip_locations profiling**

| total_rows | distinct_ips | distinct_countries | null_country |
|---|---|---|---|
| 3,239,628 | 3,239,628 | 222 | 0 |

**product_details profiling**

| total_rows | distinct_products | distinct_categories | missing_name |
|---|---|---|---|
| 18,987 | 18,986 | 47 | 0 |

## Monitoring

Cloud Function logs: **Cloud Run → gcs-to-bigquery-loader → Logs**

Check for failed loads:
```
severity=ERROR
```
