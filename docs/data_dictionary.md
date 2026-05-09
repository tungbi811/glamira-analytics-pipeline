# Data Dictionary — Glamira User Behavior Log

## Overview

| | |
|---|---|
| **Source** | MongoDB — `countly.summary` |
| **Total documents** | 41,432,473 |
| **Date range** | 2020-04-01 to 2020-06-04 |

---

## Fields

| Field | Type | Not Null | Null | Description |
|---|---|---|---|---|
| `_id` | ObjectId | 41,432,473 | 0 | MongoDB document identifier |
| `time_stamp` | int | 41,432,473 | 0 | Unix timestamp of the event |
| `local_time` | string | 41,432,233 | 240 | Local datetime string (`YYYY-MM-DD HH:MM:SS`) |
| `ip` | string | 41,432,473 | 0 | User IP address |
| `user_agent` | string | 41,432,473 | 0 | Browser/device user agent string |
| `resolution` | string | 41,432,233 | 240 | Screen resolution (e.g. `375x667`) |
| `device_id` | string | 41,432,473 | 0 | UUID identifying the device |
| `user_id_db` | string | 41,432,473 | 0 | Registered user ID (guests may have a generated ID) |
| `email_address` | string | 41,432,076 | 397 | User email address |
| `store_id` | string | 41,432,473 | 0 | Glamira store identifier (maps to country/region) |
| `api_version` | string | 41,432,473 | 0 | Tracking API version |
| `collection` | string | 41,432,473 | 0 | Event type — see [Event Types](#event-types) |
| `current_url` | string | 41,432,473 | 0 | URL where the event occurred |
| `referrer_url` | string | 41,432,473 | 0 | URL the user came from |
| `show_recommendation` | string | 33,665,625 | 7,766,848 | Whether recommendations were shown (`'true'`/`'false'`) |
| `recommendation` | bool | 10,944,359 | 68 | Whether the product was a recommendation |
| `recommendation_clicked_position` | int | 179,226 | 25,547 | Position of the clicked recommendation |
| `recommendation_product_id` | string | 217,700 | 25,596 | Product ID of the recommended item |
| `recommendation_product_position` | int/string | 38,472 | 51 | Position of recommended product in the list |
| `utm_source` | string/bool | 10,944,359 | 68 | UTM source parameter (`false` if not set) |
| `utm_medium` | string/bool | 10,944,359 | 68 | UTM medium parameter (`false` if not set) |
| `product_id` | string | 22,242,720 | 0 | Product identifier |
| `option` | array/object | 34,300,549 | 0 | Product options selected — see [Option Field](#option-field) |
| `viewing_product_id` | string | 1,989,052 | 0 | Product being viewed (used in recommendation events) |
| `cart_products` | array | 457,696 | 0 | Products in cart (present on cart/checkout events) |
| `order_id` | string/int | 114,619 | 0 | Order identifier (present on checkout events) |
| `price` | string | 186,590 | 1,311 | Product price |
| `currency` | string | 186,590 | 1,311 | Currency code |
| `is_paypal` | bool | 1,309 | 186,592 | Whether payment was via PayPal |
| `collect_id` | string | 12,043,106 | 0 | Collection/category identifier |
| `cat_id` | string | 258 | 12,042,848 | Category ID (mostly null) |
| `key_search` | string | 75,200 | 163,108 | Search query string (present on search events) |

---

## Event Types

| Event | Count | Description |
|---|---|---|
| `view_listing_page` | 11,259,694 | User viewed a product listing/category page |
| `view_product_detail` | 10,944,427 | User viewed a product detail page |
| `select_product_option` | 8,844,342 | User selected a product option (alloy, stone, etc.) |
| `select_product_option_quality` | 2,231,825 | User selected a quality variant of a product option |
| `view_static_page` | 1,451,565 | User viewed a static page (about, contact, etc.) |
| `view_landing_page` | 1,434,230 | User viewed a landing page |
| `product_detail_recommendation_visible` | 1,302,362 | Recommendations became visible on product detail page |
| `view_home_page` | 1,053,420 | User viewed the home page |
| `listing_page_recommendation_visible` | 718,048 | Recommendations became visible on listing page |
| `product_detail_recommendation_noticed` | 490,780 | User noticed recommendations on product detail page |
| `view_shopping_cart` | 343,077 | User viewed the shopping cart |
| `landing_page_recommendation_visible` | 314,999 | Recommendations became visible on landing page |
| `search_box_action` | 238,308 | User performed a search |
| `add_to_cart_action` | 187,901 | User added a product to cart |
| `product_detail_recommendation_clicked` | 179,228 | User clicked a recommendation on product detail page |
| `view_my_account` | 112,066 | User viewed their account page |
| `checkout` | 88,540 | User initiated checkout |
| `landing_page_recommendation_noticed` | 58,186 | User noticed recommendations on landing page |
| `listing_page_recommendation_noticed` | 39,819 | User noticed recommendations on listing page |
| `view_all_recommend` | 33,664 | User viewed all recommendations |
| `checkout_success` | 26,079 | User completed a purchase |
| `listing_page_recommendation_clicked` | 25,545 | User clicked a recommendation on listing page |
| `landing_page_recommendation_clicked` | 20,128 | User clicked a recommendation on landing page |
| `product_view_all_recommend_clicked` | 16,682 | User clicked "view all recommendations" on product page |
| `view_sorting_relevance` | 15,284 | User viewed sorting/relevance options |
| `sorting_relevance_click_action` | 1,713 | User clicked a sorting/relevance option |
| `back_to_product_action` | 561 | User navigated back to a product |

---

## Option Field

The `option` field captures the jewelry customization options selected by the user. It is inconsistently structured in the raw data:

| Raw format | Count |
|---|---|
| Array of objects | 22,208,495 |
| Single object (dict) | 12,092,054 |
| Missing | 7,131,924 |

When normalized, each option entry has the following keys:

| Key | Description |
|---|---|
| `option_label` | Option type name |
| `option_id` | Option identifier |
| `value_label` | Selected value name |
| `value_id` | Selected value identifier |

### Known option_label values

| option_label | Count |
|---|---|
| `alloy` | 15,680,272 |
| `diamond` | 14,530,159 |
| `stone/diamonds` | 1,822,135 |
| `stone2` | 794,329 |
| `stone 2` | 156,856 |
| `stone3` | 151,716 |
| `damenring steinbesatz` | 119,381 |
| `pear` | 107,512 |
| `stonetow` | 77,495 |
| `stone 3` | 23,825 |
| `herrenring steinbesatz` | 85 |
| `stone 4` | 2 |
