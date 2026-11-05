WITH classified_trips AS (
    SELECT
        p.borough AS pickup_borough,
        CASE
            WHEN f.pickup_zone_id = f.dropoff_zone_id
                THEN 'Same zone'
            WHEN p.borough = d.borough
                THEN 'Same borough, different zone'
            WHEN d.borough IN (
                'Manhattan', 'Brooklyn', 'Queens',
                'Bronx', 'Staten Island'
            )
                THEN 'Different NYC borough'
            WHEN f.dropoff_zone_id = 265
                THEN 'Outside NYC'
            WHEN f.dropoff_zone_id = 1
                THEN 'Newark Airport'
            WHEN f.dropoff_zone_id = 264
                THEN 'Unknown destination'
            ELSE 'Unclassified destination'
        END AS movement_type
    FROM fact_trips AS f
    JOIN dim_zone AS p
        ON f.pickup_zone_id = p.zone_id
    JOIN dim_zone AS d
        ON f.dropoff_zone_id = d.zone_id
    WHERE p.borough IN (
        'Manhattan', 'Brooklyn', 'Queens',
        'Bronx', 'Staten Island'
    )
),
borough_counts AS (
    SELECT
        pickup_borough,
        COUNT(*) AS total_trips,
        COUNT(*) FILTER (
            WHERE movement_type = 'Same zone'
        ) AS same_zone_trips,
        COUNT(*) FILTER (
            WHERE movement_type = 'Same borough, different zone'
        ) AS same_borough_trips,
        COUNT(*) FILTER (
            WHERE movement_type = 'Different NYC borough'
        ) AS cross_borough_trips,
        COUNT(*) FILTER (
            WHERE movement_type = 'Outside NYC'
        ) AS outside_nyc_trips,
        COUNT(*) FILTER (
            WHERE movement_type = 'Newark Airport'
        ) AS newark_airport_trips,
        COUNT(*) FILTER (
            WHERE movement_type = 'Unknown destination'
        ) AS unknown_destination_trips,
        COUNT(*) FILTER (
            WHERE movement_type = 'Unclassified destination'
        ) AS unclassified_trips
    FROM classified_trips
    GROUP BY pickup_borough
)
SELECT
    *,
    ROUND(
        100.0 * same_zone_trips / total_trips, 2
    ) AS same_zone_pct,
    ROUND(
        100.0 * cross_borough_trips / total_trips, 2
    ) AS cross_borough_pct
FROM borough_counts
ORDER BY total_trips DESC;
