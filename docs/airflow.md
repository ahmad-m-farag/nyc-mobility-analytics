# Airflow scheduling, backfill, and recovery

## DAGs

### `nyc_monthly_etl`

Task order:

```text
initialize_warehouse -> load_month -> validate_month
```

- Schedule: `0 6 5 * *`, 06:00 on the fifth day of the month.
- Project cutoff: the scheduled DAG ends after loading August 2026.
- Concurrency: one active run, preventing simultaneous writers to DuckDB.
- Retry policy: one retry after one minute.
- Manual execution: pass `{"month": "YYYY-MM"}`.
- Scheduled execution: derives the previous calendar month from the data interval.

### `nyc_historical_backfill`

This manually triggered controller validates an inclusive range between 2025-01 and 2026-08. It branches around months outside the requested interval and triggers one monthly DAG at a time with `wait_for_completion=True`. Sequential execution respects DuckDB's single-writer model.

## Failure and recovery demonstration

A safe demonstration uses a month whose source file is temporarily unavailable in a disposable checkout or test directory:

1. Trigger `nyc_monthly_etl` for the test month without its Parquet file.
2. `load_month` raises `FileNotFoundError`; Airflow records the exception and retries once after one minute.
3. Restore or download the official file.
4. Clear the failed `load_month` and downstream `validate_month` task instances, or rerun the DAG.
5. The transaction and month-replacement logic make the rerun safe. A failed transaction leaves the previous warehouse month intact.

Do not rename production data during a live demonstration. The missing-file check itself can be demonstrated with a disposable range or clone.

## Runtime choice

The Docker stack uses PostgreSQL metadata with Airflow LocalExecutor. SQLite plus SequentialExecutor would serialize the backfill controller and the child DAG it waits for, causing a deadlock. PostgreSQL and LocalExecutor preserve the existing DAG behavior while remaining portable on a single laptop.
