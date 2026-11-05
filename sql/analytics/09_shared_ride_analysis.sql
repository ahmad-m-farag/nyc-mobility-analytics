WITH ride_categories AS (
    SELECT
        CASE
            WHEN r.shared_requested = TRUE
             AND r.shared_matched = TRUE
                THEN 'Shared requested and matched'
            WHEN r.shared_requested = TRUE
             AND r.shared_matched = FALSE
                THEN 'Shared requested but not matched'
            WHEN r.shared_requested = FALSE
             AND r.shared_matched = FALSE
                THEN 'Sharing not requested'
            ELSE 'Other flag combination'
        END AS ride_category,
        f.trip_miles,
        f.base_passenger_fare,
        DATE_DIFF(
            'second',
            f.pickup_datetime,
            f.dropoff_datetime
        ) / 60.0 AS duration_minutes
    FROM fact_trips AS f
    JOIN dim_ride_features AS r
        ON f.ride_features_key = r.ride_features_key
),
category_stats AS (
    SELECT
        ride_category,
        COUNT(*) AS total_trips,
        ROUND(AVG(trip_miles), 2) AS avg_distance_miles,
        ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes,
        ROUND(AVG(base_passenger_fare), 2) AS avg_base_fare
    FROM ride_categories
    GROUP BY ride_category
)
SELECT
    ride_category,
    total_trips,
    ROUND(
        100.0 * total_trips / SUM(total_trips) OVER (),
        2
    ) AS trip_share_pct,
    avg_distance_miles,
    avg_duration_minutes,
    avg_base_fare
FROM category_stats
ORDER BY total_trips DESC;
