WITH daily_hourly AS (
    SELECT
        CAST(pickup_datetime AS DATE) AS trip_date,
        EXTRACT('hour' FROM pickup_datetime) AS pickup_hour,
        CASE
            WHEN EXTRACT('isodow' FROM pickup_datetime) IN (6, 7)
                THEN 'Weekend'
            ELSE 'Weekday'
        END AS day_type,
        COUNT(*) AS trips
    FROM fact_trips
    GROUP BY 1, 2, 3
)
SELECT
    day_type,
    pickup_hour,
    ROUND(AVG(trips), 2) AS avg_daily_trips,
    SUM(trips) AS total_trips
FROM daily_hourly
GROUP BY 1, 2
ORDER BY
    CASE WHEN day_type = 'Weekday' THEN 1 ELSE 2 END,
    pickup_hour;
