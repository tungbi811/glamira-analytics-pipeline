# Glamira E-Commerce Data Pipeline

End-to-end data engineering project that ingests ~41M raw user-event records from a Glamira e-commerce dataset, lands them in a cloud data warehouse, models them with dbt, and serves the results through BI dashboards.

> **Stack:** Python · MongoDB · Google Cloud (GCS, Compute Engine, Cloud Functions, BigQuery) · dbt · Looker

---

## 📐 Architecture

![Architecture diagram](docs/architecture.svg)

The pipeline is split into three phases:

1. **Ingestion** — raw NoSQL data lands on a MongoDB instance hosted on a GCE VM, enriched with IP-based geolocation and product metadata.
2. **Pipeline** — data is exported from MongoDB to Google Cloud Storage, then auto-loaded into a BigQuery raw layer via a Cloud Function trigger.
3. **Transformation & Visualization** — dbt builds a star schema (staging → core marts) on top of the raw layer; Looker reads the marts to power dashboards.

---

## 🗂️ Repository Structure

```
glamira-data-pipeline/
├── docs/                  # Architecture diagram, data dictionary, setup guides
├── ingestion/             # Phase 1 — MongoDB load, IP geolocation, product crawler
├── pipeline/              # Phase 2 — Mongo→GCS export, Cloud Functions, BQ schemas
├── dbt_glamira/           # Phase 3 — dbt project (staging + marts)
├── dashboards/            # Looker LookML and dashboard screenshots
└── notebooks/             # Exploratory data profiling
```

Each subfolder has its own README with run instructions specific to that step.