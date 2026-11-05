SELECT
    DATE_TRUNC('month', pickup_datetime)::DATE AS month,
    COUNT(*) AS total_trips,
    ROUND(SUM(base_passenger_fare), 2) AS total_base_fare,
    ROUND(AVG(base_passenger_fare), 2) AS avg_base_fare,
    ROUND(AVG(trip_miles), 2) AS avg_trip_distance_miles,
    ROUND(AVG(
        DATE_DIFF('second', pickup_datetime, dropoff_datetime)
    ) / 60.0, 2) AS avg_trip_duration_minutes
FROM fact_trips
GROUP BY 1
ORDER BY 1;
