CREATE TABLE IF NOT EXISTS dim_zone (
    zone_id BIGINT,
    borough VARCHAR,
    zone_name VARCHAR,
    service_zone VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_provider (
    provider_base_key BIGINT,
    hvfhs_license_num VARCHAR,
    base_num VARCHAR,
    provider_name VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_ride_features (
    ride_features_key BIGINT,
    shared_requested BOOLEAN,
    shared_matched BOOLEAN,
    access_a_ride BOOLEAN,
    wav_requested BOOLEAN,
    wav_matched BOOLEAN
);

CREATE TABLE IF NOT EXISTS fact_trips (
    trip_id BIGINT,
    request_datetime TIMESTAMP,
    on_scene_datetime TIMESTAMP,
    pickup_datetime TIMESTAMP,
    dropoff_datetime TIMESTAMP,
    pickup_zone_id INTEGER,
    dropoff_zone_id INTEGER,
    dispatching_provider_base_key BIGINT,
    originating_provider_base_key BIGINT,
    ride_features_key BIGINT,
    trip_miles DOUBLE,
    trip_time BIGINT,
    base_passenger_fare DOUBLE,
    tolls DOUBLE,
    bcf DOUBLE,
    sales_tax DOUBLE,
    congestion_surcharge DOUBLE,
    airport_fee DOUBLE,
    tips DOUBLE,
    driver_pay DOUBLE,
    cbd_congestion_fee DOUBLE
);

-- Populate missing taxi zones without duplicating existing records.
INSERT INTO dim_zone (
    zone_id,
    borough,
    zone_name,
    service_zone
)
SELECT
    z.LocationID,
    z.Borough,
    z.Zone,
    z.service_zone
FROM read_csv_auto('/data/taxi_zone_lookup.csv') AS z
WHERE NOT EXISTS (
    SELECT 1
    FROM dim_zone AS d
    WHERE d.zone_id = z.LocationID
);
