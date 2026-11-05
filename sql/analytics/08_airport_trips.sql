WITH airport_trips AS (
    SELECT
        CASE
            WHEN f.pickup_zone_id = 132 THEN 'JFK'
            WHEN f.pickup_zone_id = 138 THEN 'LaGuardia'
            WHEN f.pickup_zone_id = 1 THEN 'Newark'
        END AS airport,
        f.trip_miles,
        f.base_passenger_fare,
        DATE_DIFF(
            'second',
            f.pickup_datetime,
            f.dropoff_datetime
        ) / 60.0 AS duration_minutes
    FROM fact_trips AS f
    WHERE f.pickup_zone_id IN (1, 132, 138)
)
SELECT
    airport,
    COUNT(*) AS total_pickups,
    ROUND(AVG(trip_miles), 2) AS avg_distance_miles,
    ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes,
    ROUND(AVG(base_passenger_fare), 2) AS avg_base_fare,
    ROUND(SUM(base_passenger_fare), 2) AS total_base_fare
FROM airport_trips
GROUP BY airport
ORDER BY total_pickups DESC;
