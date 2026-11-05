-- Reproducible benchmark definitions. Run with the DuckDB CLI `.timer on`.
-- Each pair returns identical values and differs only in access strategy.

-- Optimization 1 baseline: function-wrapped timestamp prevents row-group pruning.
SELECT
    COUNT(*) AS trips,
    ROUND(SUM(base_passenger_fare), 2) AS total_base_fare
FROM fact_trips
WHERE strftime(pickup_datetime, '%Y-%m') = '2026-08';

-- Optimization 1: half-open range enables DuckDB min/max zone-map pruning.
SELECT
    COUNT(*) AS trips,
    ROUND(SUM(base_passenger_fare), 2) AS total_base_fare
FROM fact_trips
WHERE pickup_datetime >= TIMESTAMP '2026-08-01'
  AND pickup_datetime < TIMESTAMP '2026-09-01';

-- Optimization 2 baseline: join and aggregate the 411M-row fact table.
SELECT
    DATE_TRUNC('month', f.pickup_datetime)::DATE AS trip_month,
    p.provider_name,
    z.borough AS pickup_borough,
    COUNT(*) AS total_trips,
    ROUND(SUM(f.base_passenger_fare), 2) AS total_base_fare
FROM fact_trips AS f
JOIN dim_provider AS p
    ON f.dispatching_provider_base_key = p.provider_base_key
JOIN dim_zone AS z
    ON f.pickup_zone_id = z.zone_id
GROUP BY ALL
ORDER BY ALL;

-- Optimization 2: aggregate the dashboard summary instead.
SELECT
    trip_month,
    provider_name,
    pickup_borough,
    SUM(total_trips) AS total_trips,
    ROUND(SUM(total_base_fare), 2) AS total_base_fare
FROM agg_dashboard_trip_metrics
GROUP BY ALL
ORDER BY ALL;
