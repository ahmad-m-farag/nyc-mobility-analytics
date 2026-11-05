-- Persistent aggregate used by Superset and repeated analytical workloads.
-- Grain: pickup date x hour x provider x pickup zone x ride-sharing state.

SET memory_limit = '8GB';
SET threads = 2;
SET preserve_insertion_order = false;
SET temp_directory = '/warehouse/duckdb_temp';

BEGIN TRANSACTION;

CREATE OR REPLACE TABLE agg_dashboard_trip_metrics AS
SELECT
    CAST(f.pickup_datetime AS DATE) AS trip_date,
    DATE_TRUNC('month', f.pickup_datetime)::DATE AS trip_month,
    EXTRACT('hour' FROM f.pickup_datetime)::UTINYINT AS pickup_hour,
    CASE
        WHEN EXTRACT('isodow' FROM f.pickup_datetime) IN (6, 7)
            THEN 'Weekend'
        ELSE 'Weekday'
    END AS day_type,
    p.provider_name,
    z.zone_id AS pickup_zone_id,
    z.borough AS pickup_borough,
    z.zone_name AS pickup_zone,
    r.shared_requested,
    r.shared_matched,
    COUNT(*) AS total_trips,
    SUM(f.base_passenger_fare) AS total_base_fare,
    SUM(f.trip_miles) AS total_trip_miles,
    SUM(
        DATE_DIFF('second', f.pickup_datetime, f.dropoff_datetime)
    ) / 60.0 AS total_duration_minutes,
    SUM(CASE WHEN f.pickup_zone_id IN (1, 132, 138) THEN 1 ELSE 0 END)
        AS airport_pickup_trips
FROM fact_trips AS f
JOIN dim_provider AS p
    ON f.dispatching_provider_base_key = p.provider_base_key
JOIN dim_zone AS z
    ON f.pickup_zone_id = z.zone_id
JOIN dim_ride_features AS r
    ON f.ride_features_key = r.ride_features_key
GROUP BY ALL;

COMMENT ON TABLE agg_dashboard_trip_metrics IS
    'Superset aggregate refreshed after ETL; avoids repeated 411M-row joins.';

CREATE OR REPLACE TABLE agg_route_metrics AS
SELECT
    f.pickup_zone_id,
    f.dropoff_zone_id,
    p.borough AS pickup_borough,
    p.zone_name AS pickup_zone,
    d.borough AS dropoff_borough,
    d.zone_name AS dropoff_zone,
    COUNT(*) AS total_trips,
    SUM(f.trip_miles) AS total_trip_miles,
    SUM(f.base_passenger_fare) AS total_base_fare
FROM fact_trips AS f
JOIN dim_zone AS p
    ON f.pickup_zone_id = p.zone_id
JOIN dim_zone AS d
    ON f.dropoff_zone_id = d.zone_id
GROUP BY ALL;

COMMENT ON TABLE agg_route_metrics IS
    'Route-level aggregate for origin-destination analysis.';

CREATE OR REPLACE TABLE optimization_metadata AS
SELECT
    CURRENT_TIMESTAMP AS refreshed_at,
    COUNT(*) AS source_fact_rows,
    MIN(pickup_datetime) AS source_min_pickup,
    MAX(pickup_datetime) AS source_max_pickup
FROM fact_trips;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM agg_dashboard_trip_metrics) AS dashboard_rows,
    (SELECT COUNT(*) FROM agg_route_metrics) AS route_rows,
    (SELECT source_fact_rows FROM optimization_metadata) AS source_fact_rows;
