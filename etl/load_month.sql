-- Reusable monthly ETL
-- {{MONTH}} is replaced by the runner (YYYY-MM).

SET memory_limit = '8GB';
SET threads = 2;
SET preserve_insertion_order = false;
SET temp_directory = '/warehouse/duckdb_temp';

BEGIN TRANSACTION;


-- 1. Group exact duplicates, retaining their occurrence counts.
CREATE TEMP TABLE grouped_month AS
SELECT *, COUNT(*) AS occurrences
FROM read_parquet(
    '/data/trip_record_data/fhvhv_tripdata_{{MONTH}}.parquet'
)
GROUP BY ALL;

-- 2. Identify every applicable rejection reason.
CREATE TEMP TABLE classified_month AS
SELECT
    g.*,
    list_filter(
        [
            CASE WHEN g.pickup_datetime IS NULL
                THEN 'MISSING_PICKUP_DATETIME' END,

            CASE WHEN g.dropoff_datetime IS NULL
                THEN 'MISSING_DROPOFF_DATETIME' END,

            CASE WHEN g.pickup_datetime IS NOT NULL
                   AND g.dropoff_datetime IS NOT NULL
                   AND g.dropoff_datetime <= g.pickup_datetime
                THEN 'INVALID_DURATION' END,

            CASE WHEN g.trip_miles < 0
                THEN 'NEGATIVE_DISTANCE' END,

            CASE WHEN g.pickup_datetime IS NOT NULL
                   AND (
                       g.pickup_datetime < CAST('{{MONTH}}-01' AS TIMESTAMP)
                       OR g.pickup_datetime >=
                           CAST('{{MONTH}}-01' AS TIMESTAMP)
                           + INTERVAL '1 MONTH'
                   )
                THEN 'PICKUP_MONTH_MISMATCH' END,

            CASE WHEN g.shared_request_flag = 'N'
                   AND g.shared_match_flag = 'Y'
                THEN 'INCONSISTENT_SHARING_FLAGS' END,

            CASE WHEN
                (g.shared_request_flag IS NOT NULL
                 AND g.shared_request_flag NOT IN ('Y', 'N'))
                OR (g.shared_match_flag IS NOT NULL
                    AND g.shared_match_flag NOT IN ('Y', 'N'))
                OR (g.access_a_ride_flag IS NOT NULL
                    AND g.access_a_ride_flag NOT IN ('Y', 'N'))
                OR (g.wav_request_flag IS NOT NULL
                    AND g.wav_request_flag NOT IN ('Y', 'N'))
                OR (g.wav_match_flag IS NOT NULL
                    AND g.wav_match_flag NOT IN ('Y', 'N'))
                THEN 'INVALID_RIDE_FLAG' END,

            CASE WHEN p.zone_id IS NULL
                THEN 'UNMATCHED_PICKUP_ZONE' END,

            CASE WHEN d.zone_id IS NULL
                THEN 'UNMATCHED_DROPOFF_ZONE' END
        ],
        reason -> reason IS NOT NULL
    ) AS rejection_reasons
FROM grouped_month g
LEFT JOIN dim_zone p
    ON g.PULocationID = p.zone_id
LEFT JOIN dim_zone d
    ON g.DOLocationID = d.zone_id;

-- 3. Keep one occurrence of each valid record.
CREATE TEMP TABLE cleaned_month AS
SELECT * EXCLUDE (occurrences, rejection_reasons)
FROM classified_month
WHERE len(rejection_reasons) = 0;

-- 4. Preserve rejected records and all applicable reasons.
CREATE TABLE IF NOT EXISTS quarantined_trips AS
SELECT
    * EXCLUDE (occurrences, rejection_reasons),
    CAST('{{MONTH}}' AS VARCHAR) AS source_month,
    rejection_reasons
FROM classified_month
LIMIT 0;

-- Replace this month's previous quarantine records.
DELETE FROM quarantined_trips
WHERE source_month = '{{MONTH}}';

INSERT INTO quarantined_trips
SELECT
    c.* EXCLUDE (occurrences, rejection_reasons),
    '{{MONTH}}' AS source_month,
    CASE
        WHEN n > 1 THEN list_append(
            c.rejection_reasons, 'DUPLICATE_RECORD'
        )
        ELSE c.rejection_reasons
    END AS rejection_reasons
FROM classified_month c,
     range(1, c.occurrences + 1) AS copies(n)
WHERE len(c.rejection_reasons) > 0
   OR n > 1;

-- 4. Add new company/base combinations without
-- changing existing provider keys.
INSERT INTO dim_provider
WITH all_bases AS (
    SELECT hvfhs_license_num, dispatching_base_num AS base_num
    FROM cleaned_month
    UNION
    SELECT hvfhs_license_num, originating_base_num AS base_num
    FROM cleaned_month
),
new_bases AS (
    SELECT a.*
    FROM all_bases a
    WHERE NOT EXISTS (
        SELECT 1 FROM dim_provider d
        WHERE a.hvfhs_license_num IS NOT DISTINCT FROM d.hvfhs_license_num
          AND a.base_num IS NOT DISTINCT FROM d.base_num
    )
)
SELECT
    (SELECT COALESCE(MAX(provider_base_key), 0) FROM dim_provider)
    + ROW_NUMBER() OVER (ORDER BY hvfhs_license_num, base_num),
    hvfhs_license_num,
    base_num,
    CASE hvfhs_license_num
        WHEN 'HV0002' THEN 'Juno'
        WHEN 'HV0003' THEN 'Uber'
        WHEN 'HV0004' THEN 'Via'
        WHEN 'HV0005' THEN 'Lyft'
        ELSE 'Unknown'
    END
FROM new_bases;

-- 5. Add new ride-feature combinations.
INSERT INTO dim_ride_features
WITH combinations AS (
    SELECT DISTINCT
        shared_request_flag = 'Y' AS shared_requested,
        shared_match_flag = 'Y' AS shared_matched,
        access_a_ride_flag = 'Y' AS access_a_ride,
        wav_request_flag = 'Y' AS wav_requested,
        wav_match_flag = 'Y' AS wav_matched
    FROM cleaned_month
),
new_combinations AS (
    SELECT c.*
    FROM combinations c
    WHERE NOT EXISTS (
        SELECT 1 FROM dim_ride_features r
        WHERE c.shared_requested IS NOT DISTINCT FROM r.shared_requested
          AND c.shared_matched IS NOT DISTINCT FROM r.shared_matched
          AND c.access_a_ride IS NOT DISTINCT FROM r.access_a_ride
          AND c.wav_requested IS NOT DISTINCT FROM r.wav_requested
          AND c.wav_matched IS NOT DISTINCT FROM r.wav_matched
    )
)
SELECT
    (SELECT COALESCE(MAX(ride_features_key), 0) FROM dim_ride_features)
    + ROW_NUMBER() OVER (
        ORDER BY shared_requested, shared_matched,
                 access_a_ride, wav_requested, wav_matched
    ),
    *
FROM new_combinations;

-- 6. Connect clean trips to dimensions.
CREATE TEMP VIEW transformed_month AS
SELECT
    p.request_datetime,
    p.on_scene_datetime,
    p.pickup_datetime,
    p.dropoff_datetime,
    p.PULocationID AS pickup_zone_id,
    p.DOLocationID AS dropoff_zone_id,
    d.provider_base_key AS dispatching_provider_base_key,
    o.provider_base_key AS originating_provider_base_key,
    r.ride_features_key,
    p.trip_miles,
    p.trip_time,
    p.base_passenger_fare,
    p.tolls,
    p.bcf,
    p.sales_tax,
    p.congestion_surcharge,
    p.airport_fee,
    p.tips,
    p.driver_pay,
    p.cbd_congestion_fee
FROM cleaned_month p
LEFT JOIN dim_provider d
    ON p.hvfhs_license_num = d.hvfhs_license_num
   AND p.dispatching_base_num IS NOT DISTINCT FROM d.base_num
LEFT JOIN dim_provider o
    ON p.hvfhs_license_num = o.hvfhs_license_num
   AND p.originating_base_num IS NOT DISTINCT FROM o.base_num
LEFT JOIN dim_ride_features r
    ON (p.shared_request_flag = 'Y') IS NOT DISTINCT FROM r.shared_requested
   AND (p.shared_match_flag = 'Y') IS NOT DISTINCT FROM r.shared_matched
   AND (p.access_a_ride_flag = 'Y') IS NOT DISTINCT FROM r.access_a_ride
   AND (p.wav_request_flag = 'Y') IS NOT DISTINCT FROM r.wav_requested
   AND (p.wav_match_flag = 'Y') IS NOT DISTINCT FROM r.wav_matched;

-- 7. Ensure every trip matches every dimension.
SELECT CASE
    WHEN COUNT(*) FILTER (
        WHERE dispatching_provider_base_key IS NULL
           OR originating_provider_base_key IS NULL
           OR ride_features_key IS NULL
    ) > 0
    THEN error('Unmatched dimension keys')
    ELSE 'Dimension keys verified'
END AS validation_result
FROM transformed_month;

-- 8. Create fact table if it does not exist.
CREATE TABLE IF NOT EXISTS fact_trips AS
SELECT CAST(NULL AS BIGINT) AS trip_id, t.*
FROM transformed_month t
LIMIT 0;

-- 9. Safely replace this month's previous records.
DELETE FROM fact_trips
WHERE pickup_datetime >= CAST('{{MONTH}}-01' AS TIMESTAMP)
  AND pickup_datetime < CAST('{{MONTH}}-01' AS TIMESTAMP)
                        + INTERVAL '1 MONTH';

INSERT INTO fact_trips
SELECT
    (SELECT COALESCE(MAX(trip_id), 0) FROM fact_trips)
    + ROW_NUMBER() OVER () AS trip_id,
    t.*
FROM transformed_month t;


-- Verify source-to-warehouse reconciliation for this month.
SELECT CASE
    WHEN (SELECT SUM(occurrences) FROM grouped_month)
       <> (SELECT COUNT(*) FROM cleaned_month)
        + (SELECT COUNT(*) FROM quarantined_trips
           WHERE source_month = '{{MONTH}}')
    THEN error('Raw/accepted/quarantine reconciliation failed')
    ELSE 'Reconciliation verified'
END AS validation_result;

COMMIT;

-- 10. Report the result.
SELECT COUNT(*) AS loaded_trips
FROM fact_trips
WHERE pickup_datetime >= CAST('{{MONTH}}-01' AS TIMESTAMP)
  AND pickup_datetime < CAST('{{MONTH}}-01' AS TIMESTAMP)
                        + INTERVAL '1 MONTH';
