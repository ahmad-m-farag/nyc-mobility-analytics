# ETL and data quality

## Transactional monthly load

`etl/load_month.sql` is parameterized by `YYYY-MM` and wraps each month in one transaction. A rerun deletes and replaces only the selected month from `fact_trips` and `quarantined_trips`. Dimension inserts use anti-joins, so existing surrogate keys remain stable.

The ETL runs with:

```sql
SET memory_limit = '8GB';
SET threads = 2;
SET preserve_insertion_order = false;
```

## Classification rules

| Rule | Action |
|---|---|
| Missing pickup timestamp | Quarantine: `MISSING_PICKUP_DATETIME` |
| Missing drop-off timestamp | Quarantine: `MISSING_DROPOFF_DATETIME` |
| Drop-off not after pickup | Quarantine: `INVALID_DURATION` |
| Negative trip distance | Quarantine: `NEGATIVE_DISTANCE` |
| Pickup outside the source month | Quarantine: `PICKUP_MONTH_MISMATCH` |
| Shared matched while sharing was not requested | Quarantine: `INCONSISTENT_SHARING_FLAGS` |
| Ride flag outside `Y`, `N`, or null | Quarantine: `INVALID_RIDE_FLAG` |
| Unmatched pickup or drop-off location | Quarantine with the relevant zone reason |
| Exact duplicate occurrence after the first | Quarantine: `DUPLICATE_RECORD` |

A record may have more than one reason. Therefore reason counts may exceed the number of quarantined rows.

## Measured results

| Outcome | Count |
|---|---:|
| Raw | 411,776,395 |
| Accepted | 411,739,486 |
| Quarantined | 36,909 |
| Difference | 0 |

| Rejection reason | Affected rows |
|---|---:|
| Inconsistent sharing flags | 24,657 |
| Invalid duration | 12,237 |
| Exact duplicate occurrence | 17 |

The validation task also checks for zero invalid accepted timestamps/distances, zero unresolved dimension keys, zero inconsistent accepted sharing flags, zero unmatched zones, and zero quarantine rows without reasons.

## Schema handling

DuckDB reads the official Parquet schema directly. The selected first and last files both expose the expected 24 fields, including `cbd_congestion_fee`. The current project window did not require a schema-union repair. The ETL names source columns explicitly when transforming them, so an incompatible future schema fails visibly instead of silently shifting data.
