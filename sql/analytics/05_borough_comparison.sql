WITH borough_stats AS (
    SELECT
        z.borough,
        COUNT(*) AS total_trips,
        ROUND(AVG(f.trip_miles), 2) AS avg_trip_miles,
        ROUND(AVG(f.base_passenger_fare), 2) AS avg_base_fare,
        ROUND(SUM(f.base_passenger_fare), 2) AS total_base_fare
    FROM fact_trips AS f
    JOIN dim_zone AS z
        ON f.pickup_zone_id = z.zone_id
    WHERE z.borough IN (
        'Manhattan',
        'Brooklyn',
        'Queens',
        'Bronx',
        'Staten Island'
    )
    GROUP BY z.borough
)
SELECT
    borough,
    total_trips,
    ROUND(
        100.0 * total_trips / SUM(total_trips) OVER (),
        2
    ) AS pickup_share_pct,
    avg_trip_miles,
    avg_base_fare,
    total_base_fare
FROM borough_stats
ORDER BY total_trips DESC;
