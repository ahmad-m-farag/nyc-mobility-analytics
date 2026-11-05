WITH route_stats AS (
    SELECT
        f.pickup_zone_id,
        f.dropoff_zone_id,
        p.borough AS pickup_borough,
        p.zone_name AS pickup_zone,
        d.borough AS dropoff_borough,
        d.zone_name AS dropoff_zone,
        COUNT(*) AS total_trips,
        ROUND(AVG(f.trip_miles), 2) AS avg_trip_miles,
        ROUND(AVG(f.base_passenger_fare), 2) AS avg_base_fare
    FROM fact_trips AS f
    JOIN dim_zone AS p
        ON f.pickup_zone_id = p.zone_id
    JOIN dim_zone AS d
        ON f.dropoff_zone_id = d.zone_id
    WHERE p.borough IN (
        'Manhattan', 'Brooklyn', 'Queens',
        'Bronx', 'Staten Island'
    )
    AND d.borough IN (
        'Manhattan', 'Brooklyn', 'Queens',
        'Bronx', 'Staten Island'
    )
    AND f.pickup_zone_id <> f.dropoff_zone_id
    GROUP BY 1, 2, 3, 4, 5, 6
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY total_trips DESC, pickup_zone_id, dropoff_zone_id
    ) AS route_rank,
    pickup_borough,
    pickup_zone,
    dropoff_borough,
    dropoff_zone,
    total_trips,
    avg_trip_miles,
    avg_base_fare
FROM route_stats
ORDER BY route_rank
LIMIT 15;
