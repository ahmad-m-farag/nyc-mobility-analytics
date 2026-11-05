WITH zone_activity AS (
    SELECT
        z.zone_id,
        z.borough,
        z.zone_name,
        COUNT(*) AS total_pickups,
        ROUND(AVG(f.trip_miles), 2) AS avg_trip_miles
    FROM fact_trips AS f
    JOIN dim_zone AS z
        ON f.pickup_zone_id = z.zone_id
    GROUP BY
        z.zone_id,
        z.borough,
        z.zone_name
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY total_pickups DESC, zone_id
    ) AS pickup_rank,
    borough,
    zone_name,
    total_pickups,
    ROUND(
        100.0 * total_pickups
        / SUM(total_pickups) OVER (),
        2
    ) AS pickup_share_pct,
    avg_trip_miles
FROM zone_activity
ORDER BY pickup_rank
LIMIT 15;
