WITH categorized_trips AS (
    SELECT
        CASE
            WHEN trip_miles IS NULL THEN 'Unknown distance'
            WHEN trip_miles = 0 THEN '0 miles'
            WHEN trip_miles < 1 THEN 'Under 1 mile'
            WHEN trip_miles < 3 THEN '1–3 miles'
            WHEN trip_miles < 5 THEN '3–5 miles'
            WHEN trip_miles < 10 THEN '5–10 miles'
            WHEN trip_miles < 20 THEN '10–20 miles'
            ELSE '20+ miles'
        END AS distance_category,
        CASE
            WHEN trip_miles IS NULL THEN 8
            WHEN trip_miles = 0 THEN 1
            WHEN trip_miles < 1 THEN 2
            WHEN trip_miles < 3 THEN 3
            WHEN trip_miles < 5 THEN 4
            WHEN trip_miles < 10 THEN 5
            WHEN trip_miles < 20 THEN 6
            ELSE 7
        END AS category_order,
        trip_miles,
        base_passenger_fare,
        DATE_DIFF(
            'second',
            pickup_datetime,
            dropoff_datetime
        ) / 60.0 AS duration_minutes
    FROM fact_trips
)
SELECT
    distance_category,
    COUNT(*) AS total_trips,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
        2
    ) AS trip_share_pct,
    ROUND(AVG(trip_miles), 2) AS avg_distance_miles,
    ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes,
    ROUND(AVG(base_passenger_fare), 2) AS avg_base_fare,
    ROUND(
        AVG(base_passenger_fare / NULLIF(trip_miles, 0)),
        2
    ) AS avg_base_fare_per_mile
FROM categorized_trips
GROUP BY distance_category, category_order
ORDER BY category_order;
