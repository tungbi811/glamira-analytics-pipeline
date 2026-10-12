# BigQuery raw layer profiling

Profile of `raw.summary`, `raw.ip_locations` and `raw.products` after the first load (export run `20261012T080352` for summary, 2026-10-12). Queries: [`load/profile.sql`](../../load/profile.sql), about 27 GB scanned.

## Summary

| Check | Result | Action in dbt |
|---|---|---|
| Row counts | summary 41,432,473 · ip_locations 3,239,628 · products 19,417, all equal to MongoDB | none |
| Keys | `_id`, `ip`, `product_id` unique in their tables | add `unique` tests |
| Time range | **2020-04-01 00:00 → 2020-06-04 10:21 UTC** (65 days); last day is partial | exclude or flag 2020-06-04 in daily metrics |
| IP join | 100% of events find their IP; 98.88% have a country | none |
| Product join (product events) | 98.46% `ok`, 1.54% `not_found`, 0% never crawled | none |
| Product join (ordered items) | **80.7% `ok`, 2.2% `not_found`, 17.1% never crawled** (94 products, all free gifts) | flag `price = 0` lines as `is_free_gift` (see 4) |
| Orders | 26,079 `checkout_success` rows, 26,031 distinct `order_id` | deduplicate on `order_id` |

## 1. Volume and time range

- **65 days of data, April 1 to June 4, 2020.** The archive name says 2019, and the first samples showed June, but the full range starts in April.
- Daily volume grows from about 400k events (early April) to about 850k (mid-May), then eases to about 720k. No gaps. 2020-06-04 has only 205k events because collection stops at 10:21 UTC.
- `time_stamp` parses as whole seconds on every row.

## 2. Completeness

| Field | Missing |
|---|---:|
| `ip`, `device_id`, `store_id`, `current_url` | 0% |
| `local_time` | 240 rows |
| `user_id_db` | 95.2% |
| `email_address` | 95.2% |

Only about 5% of events come from logged-in users (31,127 distinct `user_id_db`). **`device_id` is the visitor key** (7,691,556 devices), not `user_id_db`.

Fields per event type (from query 2b):

| Field | Present on |
|---|---|
| `product_id` | `view_product_detail`, `select_product_option*`, `add_to_cart_action`, `view_all_recommend`, `back_to_product_action` (100% each) |
| `viewing_product_id` | `product_detail_recommendation_*`, `product_view_all_recommend_clicked` |
| `price` | only `add_to_cart_action` (186,588 of 187,901) |
| `cart_products` | `checkout_success` and `checkout` (100%), `view_shopping_cart` (73%) |
| `order_id` | only `checkout_success` |
| `key_search` | `search_box_action`, **66,739 of 238,308 (28%)**. Earlier samples suggested it was always null; it isn't |
| `option` | product and listing events. On listing pages it holds the active filters |

## 3. Distinct values

| | Count |
|---|---:|
| stores (`store_id`) | 86 |
| IPs | 3,239,628 |
| devices | 7,691,556 |
| logged-in users | 31,127 |
| orders | 26,031 |

**Stores:** each `store_id` maps to one website host (query 3b). Largest: 6 = .de (5.2M events), 7 = .co.uk, 12 = .fr, 41 = .com, 14 = .it. Things the store lookup must handle:

- **Several ids share a host:** .be (32, 33), .ch (10, 35, 61), .ca (38, 39), .com (41, 68), .hk (47, 48), .sg (37, 77), .tw (96, 97), .az (95, 98), .africa (80, 81, 83). These are likely language versions of one country site.
- **Store 1 is `ring-paare.de`**, a separate brand.
- **Stores 24 and 78 are `glamira.local`** with 1 event each: test traffic, to exclude.

**Orders:** 48 `checkout_success` rows repeat an `order_id` (26,079 rows vs 26,031 orders). Keep one row per order.

## 4. Join coverage

- **IP → location:** every event IP is in `ip_locations`. 1.12% of events have no country (IP2Location could not resolve the IP).
- **Product events → products:** 98.46% `ok`. The 1.54% `not_found` are products removed from the site since 2020.
- **Ordered items → products: 17.1% never crawled.** The crawler took ids from the 7 product events only, so ordered products that never appeared on those events were skipped. That is 94 distinct products but 6,000 order lines. Across all `cart_products` (including `checkout` and `view_shopping_cart`), 140 distinct ids are missing.
  - **They are free gifts.** 5,999 of the 6,000 lines have price `0,00`, and the most frequent ids are promotional pendants added to orders automatically (109814 "Free Pendant - Billy", 108669 "Free Pendant - Pomona", 104330 "Free Pendant - Meriem", checked on glamira.com). Only 1 paid order line has no crawled product.
  - **Decision: not crawled.** Revenue is unaffected. dbt flags `price = 0` lines as `is_free_gift` and leaves them out of product rankings.

## 5. Formats dbt has to parse

**Prices** (`price`, `cart_products[].price`) are locale-formatted text. Seen patterns:

| Pattern | Example | Currency |
|---|---|---|
| `999,99` | `397,00` | €, kr, CAD $ |
| `999.99` | `241.00` | £, $, CHF, AU $, € |
| `9.999,99` | `1.356,00` | €, kr, RON, ₺ |
| `9,999.99` | `1,069.00` | $, AU $, £, MXN $ |
| `9 999,99` | `7 423,00` | kr, €, zł, Kč, Ft |
| `999.999,99` | `144.659,00` | CLP |

Parsing rule: **the last `.` or `,` followed by exactly 2 digits is the decimal separator.** Remove every other `.`, `,` and space, then cast to NUMERIC. Also:

- the currency is a symbol, and the same symbol means different currencies (`kr` = SEK, DKK or NOK; `$` = USD or others), so currency must come from the store, not the symbol
- some currencies are odd (`CHF '`), and 506 order lines have an empty currency
- many order lines are `0,00` / `0.00` (free items), so revenue must not count them as products sold

**`local_time`** is not zero-padded: `2020-04-04 4:51:42`, `2020-05-25 1:7:25`, `2020-05-23 7:7:9`. Only 18% of rows have the padded `99:99:99` form. Use `SAFE.PARSE_DATETIME('%Y-%m-%d %H:%M:%S', local_time)`, and prefer `time_stamp` (UTC) for event time.

**`utm_source` / `utm_medium`** have two "no campaign" values: `NULL` (30.5M rows) and `'false'` (10.9M). Map both to NULL. Real sources: `criteo / retargeting` (64k), internal `recommendation / *` (23k), `instagram / social`, `zalo`. Some rows have `utm_medium` set to a country code (`false / US`).

**`option`** after export normalization:

- Labels are inconsistent: `stone2` vs `stone 2`, German labels (`damenring steinbesatz`, `Kollektion`)
- About 12M rows came from the flat-object shape (`option_id` NULL), mostly `alloy`, `diamond`, `shapediamond`
- `view_all_recommend` options hold product metadata (`price`, `category id`, `Kollektion`), not customer choices

**`products`:** 18,981 `ok` across 15 product types; 1 `ok` product has a price that isn't a plain number. The 436 `not_found` rows have no name or price, as expected.
