# Performance optimization benchmarks

## Method

Benchmarks ran on 5 November 2026 with the pinned `duckdb/duckdb:1.5.6` image against the 411,739,486-row production fact table. Every query used a read-only database connection, two threads, and an 8 GB memory limit. The script first performs exact result-equivalence checks and aborts if either pair differs. It then alternates baseline and optimized variants for three repetitions. Each timed query runs in a fresh DuckDB container and writes its complete result to `/dev/null`, so result rendering is not included but the query is fully consumed. DuckDB's `.timer` supplies the recorded query time.

The saved evidence is `artifacts/benchmarks/optimization_benchmarks_2026-11-05.csv`. It records every execution time, the medians, speedups, configuration, equivalence result, and result summary. Host and operating-system caches can affect absolute timings, but no result cache is used or counted as an optimization.

## Optimization 1: sargable timestamp range

The original filter formats every timestamp before comparison:

```sql
WHERE strftime(pickup_datetime, '%Y-%m') = '2026-08'
```

The optimized half-open range preserves the raw column and enables DuckDB row-group min/max zone-map pruning:

```sql
WHERE pickup_datetime >= TIMESTAMP '2026-08-01'
  AND pickup_datetime < TIMESTAMP '2026-09-01'
```

Both returned 20,490,900 trips and $552,408,127.14 base fare.

| Run | Original | Optimized |
|---:|---:|---:|
| 1 | 8.677 s | 0.146 s |
| 2 | 8.419 s | 0.140 s |
| 3 | 8.535 s | 0.167 s |
| Median | 8.535 s | 0.146 s |

Median speedup: **58.5x**. The exact scalar outputs matched: 20,490,900 trips and $552,408,127.14.

## Optimization 2: persistent dashboard aggregate

The baseline joins `fact_trips` to provider and zone dimensions, then groups by month, provider, and borough. The optimized query rolls up `agg_dashboard_trip_metrics`, which is already grouped at date/hour/provider/zone/sharing grain.

Both produced 256 groups, 411,739,486 trips, and $11,168,662,827.90 base fare.

| Run | Fact join and group | Aggregate rollup |
|---:|---:|---:|
| 1 | 14.415 s | 0.281 s |
| 2 | 13.561 s | 0.259 s |
| 3 | 13.655 s | 0.296 s |
| Median | 13.655 s | 0.281 s |

Median speedup: **48.6x**. A two-way `EXCEPT ALL` check found no differing rows. Both variants returned 256 groups totaling 411,739,486 trips and $11,168,662,827.90.

The refresh scanned the fact table once, took 76 seconds in total for both aggregate tables, and created 11,039,719 dashboard rows plus 66,347 route rows. This cost is paid after ETL rather than on every dashboard interaction.

## Reproduction

```bash
docker compose --profile tools run --rm warehouse-optimize
./scripts/benchmark_optimizations.sh
```

The script writes a dated CSV under `artifacts/benchmarks/`. Override the repetition count or output path only when needed:

```bash
BENCHMARK_RUNS=5 BENCHMARK_OUTPUT=artifacts/benchmarks/custom.csv \
  ./scripts/benchmark_optimizations.sh
```

The canonical statements are also documented in `sql/optimizations/benchmark.sql`.
