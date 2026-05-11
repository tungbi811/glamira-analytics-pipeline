# Transform — dbt (BigQuery)

Builds a star schema on top of `glamira_raw` using dbt. Runs after all three BigQuery tables are loaded.

## Layer structure

| Layer | Schema | Materialization |
|---|---|---|
| Staging | `glamira_staging` | View |
| Intermediate | — | Ephemeral |
| Marts (dimensions + facts) | `glamira_marts` | Table |

## Run

```bash
cd transform
dbt run
dbt test
```
