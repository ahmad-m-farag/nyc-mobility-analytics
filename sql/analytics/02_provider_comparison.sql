SELECT
    p.provider_name,
    COUNT(*) AS total_trips,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
        2
    ) AS trip_share_pct,
    ROUND(AVG(f.base_passenger_fare), 2) AS avg_base_fare,
    ROUND(AVG(f.trip_miles), 2) AS avg_trip_distance_miles,
    ROUND(
        AVG(DATE_DIFF(
            'second',
            f.pickup_datetime,
            f.dropoff_datetime
        )) / 60.0,
        2
    ) AS avg_trip_duration_minutes
FROM fact_trips AS f
JOIN dim_provider AS p
    ON f.dispatching_provider_base_key = p.provider_base_key
GROUP BY
    p.provider_name
ORDER BY
    total_trips DESC;
