# Data dictionary

All collections live in the `glamira` MongoDB database on the VM.

| Collection | Rows | Built by | Section |
|---|---:|---|---|
| `summary` | 41,432,473 | `ingest/import_events.sh` | [Events](#events) |
| `ip_locations` | 3,239,628 | `ingest/lookup_ips.py` | [ip_locations](#ip_locations) |
| `products` | 19,417 | `ingest/crawl_products.py` | [products](#products) |
| `product_ids` | 19,417 | `ingest/crawl_products.py` | working list for the crawler, not exported |

---

## `summary`

Raw clickstream from Glamira's country stores (glamira.de, .fr, .co.uk, ...): one document = one user action on the site.

- **Source:** `gs://<bucket>/source/glamira_ubl_2019.tar.gz` (mongodump), restored by `ingest/import_events.sh`
- **Size:** 41,432,473 documents, 27 event types
- **Profiling files:** [`profiling/event_counts.json`](profiling/event_counts.json) (full scan), [`profiling/schema_sample.json`](profiling/schema_sample.json) (Compass schema, 1,000-doc sample)
- **Checked against:** one real document each of `view_product_detail`, `select_product_option`, `add_to_cart_action`, `checkout_success`, `product_detail_recommendation_clicked`, `search_box_action`

Rows marked *(verify)* are still inferred from field names only.

## Events

The event type is stored in the `collection` field.

### Purchase funnel

How many events of each step happen, compared with the step before.

| Step | Event | Count | Conversion from previous step |
|---|---|---:|---:|
| 1 | `view_product_detail` | 10,944,427 | n/a |
| 2 | `add_to_cart_action` | 187,901 | 1.7% |
| 3 | `checkout` | 88,540 | 47.1% |
| 4 | `checkout_success` | 26,079 | 29.5% |

For every 100 product views there are about 1.7 add-to-carts. Overall, about 0.24% of product views turn into a completed order.

These are **event counts, not unique users**. One person can view a product many times or open checkout twice, so treat the rates as rough. The real per-session funnel gets built in dbt.

### All event types

| Group | Event | Count |
|---|---|---:|
| Page views | `view_listing_page` | 11,259,694 |
| | `view_product_detail` | 10,944,427 |
| | `view_static_page` | 1,451,565 |
| | `view_landing_page` | 1,434,230 |
| | `view_home_page` | 1,053,420 |
| | `view_shopping_cart` | 343,077 |
| | `view_my_account` | 112,066 |
| Product options | `select_product_option` | 8,844,342 |
| | `select_product_option_quality` | 2,231,825 |
| Cart & checkout | `add_to_cart_action` | 187,901 |
| | `checkout` | 88,540 |
| | `checkout_success` | 26,079 |
| | `back_to_product_action` | 561 |
| Recommendations: product page | `product_detail_recommendation_visible` | 1,302,362 |
| | `product_detail_recommendation_noticed` | 490,780 |
| | `product_detail_recommendation_clicked` | 179,228 |
| Recommendations: listing page | `listing_page_recommendation_visible` | 718,048 |
| | `listing_page_recommendation_noticed` | 39,819 |
| | `listing_page_recommendation_clicked` | 25,545 |
| Recommendations: landing page | `landing_page_recommendation_visible` | 314,999 |
| | `landing_page_recommendation_noticed` | 58,186 |
| | `landing_page_recommendation_clicked` | 20,128 |
| Recommendations: other | `view_all_recommend` | 33,664 |
| | `product_view_all_recommend_clicked` | 16,682 |
| Search & sorting | `search_box_action` | 238,308 |
| | `view_sorting_relevance` | 15,284 |
| | `sorting_relevance_click_action` | 1,713 |
| **Total** | | **41,432,473** |

## Fields

### Present on every event

| Field | Type | Example | Meaning |
|---|---|---|---|
| `_id` | ObjectId | `5ed8cb2bc671fc36b74653ad` | MongoDB document id |
| `collection` | string | `view_product_detail` | Event type (see above) |
| `time_stamp` | integer | `1591266092` | Event time, Unix epoch **seconds**, UTC (= 2020-06-04 10:21:32 UTC) |
| `local_time` | string | `2020-06-04 12:21:27` | Event time in the store's local time zone (.fr = UTC+2, .co.uk = UTC+1). Not zero-padded: `12:21:4` occurs |
| `ip` | string | (hidden) | Visitor IP address. Input for the IP → location lookup. **PII** |
| `user_agent` | string | (hidden) | Browser user-agent string. Device, OS and browser can be parsed from it |
| `resolution` | string | `375x667` | Screen size `WIDTHxHEIGHT` in px; small widths = mobile |
| `device_id` | string | (hidden) | Anonymous browser/device id |
| `user_id_db` | string | (hidden) | Logged-in customer id; empty when not logged in *(verify)* |
| `email_address` | string | (hidden) | Customer email when known. **PII** |
| `store_id` | string | `12` | Country store. Seen so far: `6` = .de, `7` = .co.uk, `11` = .nl, `12` = .fr, `50` = .pl |
| `api_version` | string | `1.0` | Tracking API version |
| `current_url` | string | `https://www.glamira.fr/glamira-pendant-viktor.html?alloy=yellow-375` | Page where the event happened. Product pages are `<slug>.html?<options>`. Input for the product crawler |
| `referrer_url` | string | `https://www.glamira.fr/men-s-necklaces/` | Previous page. Can contain ad-click params (`gclid=...`) |
| `show_recommendation` | string | `'false'` | Whether recommendations were shown. The **string** `'false'`, not a boolean |

### Product fields

On `view_product_detail`, `select_product_option`, `add_to_cart_action`.

| Field | Type | Example | Meaning |
|---|---|---|---|
| `product_id` | string | `'110474'` | Product being viewed or acted on |
| `option` | array | `[{option_label: 'alloy', option_id: '198911', value_label: 'red-750', value_id: '1593626'}]` | Product options chosen (metal, stone, ...). IDs are strings; values are often empty `''` |
| `price` | string | `'1 278,00'` | Price as **locale-formatted text** (space thousands, comma decimal on .fr) |
| `currency` | string | `€` | Currency **symbol**, not ISO code |
| `is_paypal` | null | `null` | Payment-method flag. Null on every doc seen so far |
| `cat_id` | null | | Category id. Null in the sample *(verify)* |

### Cart and order fields

On `checkout_success` (and likely `checkout`, `view_shopping_cart` *(verify)*).

| Field | Type | Example | Meaning |
|---|---|---|---|
| `order_id` | **integer** here, string in the schema sample | `720251727` | Order id |
| `cart_products` | array | see below | One entry per item in the order |
| `cart_products[].product_id` | integer | `96047` | Product id (integer, unlike top-level `product_id`) |
| `cart_products[].amount` | integer | `1` | Quantity |
| `cart_products[].price` | string | `'880.00'` | Unit price as text |
| `cart_products[].currency` | string | `£` | Currency symbol |
| `cart_products[].option` | array | `[{option_label: 'alloy', option_id: 152820, value_label: 'Weißgold 585', value_id: 1156867}]` | Options; IDs are **integers** here; labels are localized (German label on the UK store) |

### Recommendation fields

On `*_recommendation_*` events.

| Field | Type | Example | Meaning |
|---|---|---|---|
| `viewing_product_id` | string | `'102107'` | Product page the user was on |
| `recommendation_product_id` | string | `'102110'` | Recommended product that was clicked |
| `recommendation_clicked_position` | integer | `0` | Slot clicked, **0-based** (0 = first) |
| `recommendation` | boolean | `false` | Recommendation flag on page-view events |

### Marketing and search fields

| Field | Type | Example | Meaning |
|---|---|---|---|
| `utm_source` | boolean / string | `false` | Campaign source; `false` = no UTM |
| `utm_medium` | boolean / string | `false` | Campaign medium; `false` = no UTM |
| `key_search` | null | `null` | Search keyword. **Null even on `search_box_action`**, so the keyword was likely never captured |
| `collect_id` | string | | Unknown *(verify)* |

## Data quality notes

These affect the Phase 2 export (MongoDB → Parquet → BigQuery), because a BigQuery column needs one fixed type.

1. **The data is from 2020.** The samples are dated 2020-06-04, but the archive is named "2019". Check the real range with `min`/`max` of `time_stamp` before profiling.
2. **`option` has two shapes.**
   - Usually an array of `{option_id, option_label, value_id, value_label}`, all strings, with values often empty `''`
   - Sometimes a flat object `{alloy, diamond, stone, ...}`, with mixed-case keys like `Kollektion` (schema sample)
   - Plan: normalize to one array-of-records shape on export, or keep it as a JSON string in `raw`.
3. **Numbers stored as text.** `price` is locale-formatted (`'1 278,00'` vs `'880.00'`), and `currency` is a symbol (`€`, `£`). Parsing needs the store's locale.
4. **IDs change type by location.**
   - `product_id`: string at top level, integer in `cart_products`
   - `option_id` and `value_id`: strings in `option`, integers in `cart_products[].option`
   - `order_id`: integer or string
   - Plan: cast all IDs to string.
5. **Booleans stored inconsistently.** `show_recommendation` is the string `'false'`, while `utm_*` mix `false` and strings. Convert to BOOL or null.
6. **Time:** use `time_stamp` (UTC seconds) as the source of truth. `local_time` is a string in store time and isn't zero-padded (`12:21:4`), so don't parse it as the main timestamp.
7. **Empty fields:** `key_search` is null even on search events. `cat_id` and `is_paypal` are null in every doc seen. Check with a full scan before dropping them.
8. **Localized labels:** option `value_label` depends on the store language (`Weißgold 585`), so group by `value_id`, not by label.
9. **PII:** `ip`, `email_address`, `device_id`, `user_id_db`. Keep them in `raw` and exclude or hash them in models exposed to dashboards.
10. **Sample limits:** the schema comes from 1,000 docs, so rare fields and types may be missing. Confirm with the query below.

## Verify field presence per event

Run on the VM in tmux (`make ssh`, then `mongosh`). It reads every field of every document, so expect 30+ minutes.

```js
db.summary.aggregate([
  { $project: { collection: 1, keys: { $objectToArray: "$$ROOT" } } },
  { $unwind: "$keys" },
  { $group: { _id: { event: "$collection", field: "$keys.k" }, n: { $sum: 1 } } },
  { $sort: { "_id.event": 1, n: -1 } }
], { allowDiskUse: true })
```

---

## `ip_locations`

One document per unique IP in `summary`, resolved with the IP2Location DB3 file (`gs://<bucket>/source/ip2location_db3.bin`).

- **Rows:** 3,239,628 unique IPs
- **Unresolved:** 38,242 (1.2%): private, invalid or IPv6 addresses. The DB3 file is IPv4 only
- **Rebuild:** `uv run ingest/lookup_ips.py` on the VM (~8 min). Writes `ip_locations_tmp`, then swaps it in, so a failed run keeps the old table
- **Join:** `summary.ip = ip_locations.ip` (unique index on `ip`)

| Field | Type | Example | Meaning |
|---|---|---|---|
| `ip` | string | `81.2.69.142` | IP address, same format as `summary.ip`. **PII** |
| `country_code` | string / null | `GB` | ISO 3166-1 alpha-2 country code |
| `country` | string / null | `United Kingdom` | Country name (English) |
| `region` | string / null | `England` | Region / state |
| `city` | string / null | `Bracknell` | City |

All location fields are null when the IP can't be resolved. IP2Location's own markers (`-`, `INVALID IP ADDRESS`) are converted to null.

---

## `products`

One document per product id seen in the events, crawled from glamira.com.

- **Input:** `product_ids`, the unique ids from 7 product events (`product_id`, or `viewing_product_id` for `product_view_all_recommend_clicked`)
- **Source:** `https://www.glamira.com/productcustomizer/reactdata/index/id/<product_id>/`, the JSON endpoint the product page loads. The `.com` store gives English names; the country stores return localized names
- **Rebuild:** `uv run ingest/crawl_products.py` (~1.5–3 h). Resumable: products already `ok` or `not_found` are skipped; `error` ones are retried
- **Join:** `summary.product_id = products.product_id` (both strings; unique index on `product_id`)
- **Last crawl (2026-10-12):** 19,417 ids: 18,981 `ok` (97.8%), 436 `not_found` (2.2%), 0 `error`. The v1 crawl gave 18,987 / 431 for 19,418 ids

| Field | Type | Example | Meaning |
|---|---|---|---|
| `product_id` | string | `'110474'` | Product id, stored as string to match `summary` |
| `status` | string | `ok` | `ok` = crawled, `not_found` = 404 (product removed from the site), `error` = failed, see `error` |
| `error` | string | `HTTP 403` | Failure reason; only on `status: error` |
| `crawled_at` | datetime (UTC) | `2026-10-12T05:11:51Z` | When the product was fetched |
| `name` | string | `GLAMIRA Men's Pendant Viktor` | Product name (English) |
| `sku` | string | `Men-Viktor` | Product SKU |
| `product_type` | string | `pendant` | Product type: `ring`, `wedding_ring`, `pendant`, `bracelet`, ... |
| `collection` | string | `symbols` | Product collection (not the event type in `summary.collection`) |
| `collection_id` | string | `'5157'` | Collection id |
| `gender` | string | `men` | Target gender: `men`, `women`, `kids`, ... |
| `attribute_set` | string | `diamonds` | Product attribute group |
| `type_id` | string | `simple` | Magento product type |
| `category` | integer | `0` | Category id; `0` / empty on samples seen |
| `category_name` | string | `''` | Category name; empty on samples seen |
| `price` | string | `'279.000000'` | Default-configuration price on glamira.com, as text. **Today's price**, not the 2020 price |
| `min_price` | string | `'141.000000'` | Cheapest configuration |
| `max_price` | string | `'2541.000000'` | Most expensive configuration |
| `store_code` | string | `glus` | Store the data came from (`glus` = glamira.com) |
| `raw` | object | | Full JSON response, kept so new fields can be extracted without re-crawling |

### Crawl notes

- **Run from a local machine, not the VM.** glamira.com sits behind Akamai, which returns `403 Access Denied` for Google Cloud IPs (tested two VM IPs and five browser fingerprints, all 403). The crawler runs on a laptop and writes to the VM's MongoDB through `make tunnel`. Airflow treats `products` as a one-time backfill.
- **Browser fingerprint needed.** Plain `curl` / `requests` also get 403 from home IPs, because Akamai checks the TLS handshake. `curl_cffi` with `impersonate="chrome"` passes.
- **Prices are from the crawl date** (2026), not from when the events happened (2020). For revenue, use `summary.cart_products[].price` on `checkout_success`.
