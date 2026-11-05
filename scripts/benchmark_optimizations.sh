#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNS="${BENCHMARK_RUNS:-3}"
BENCHMARK_DATE="${BENCHMARK_DATE:-$(date +%F)}"
OUTPUT_FILE="${BENCHMARK_OUTPUT:-$PROJECT_DIR/artifacts/benchmarks/optimization_benchmarks_${BENCHMARK_DATE}.csv}"
DUCKDB_IMAGE="${DUCKDB_IMAGE:-duckdb/duckdb:1.5.6}"
DATABASE_PATH="/project/warehouse/nyc_mobility.duckdb"

if ! [[ "$RUNS" =~ ^[1-9][0-9]*$ ]]; then
    echo "BENCHMARK_RUNS must be a positive integer" >&2
    exit 2
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

BASELINE_1="
SELECT COUNT(*) AS trips, ROUND(SUM(base_passenger_fare), 2) AS total_base_fare
FROM fact_trips
WHERE strftime(pickup_datetime, '%Y-%m') = '2026-08'
"

OPTIMIZED_1="
SELECT COUNT(*) AS trips, ROUND(SUM(base_passenger_fare), 2) AS total_base_fare
FROM fact_trips
WHERE pickup_datetime >= TIMESTAMP '2026-08-01'
  AND pickup_datetime < TIMESTAMP '2026-09-01'
"

BASELINE_2="
SELECT
    DATE_TRUNC('month', f.pickup_datetime)::DATE AS trip_month,
    p.provider_name,
    z.borough AS pickup_borough,
    COUNT(*) AS total_trips,
    ROUND(SUM(f.base_passenger_fare), 2) AS total_base_fare
FROM fact_trips AS f
JOIN dim_provider AS p
    ON f.dispatching_provider_base_key = p.provider_base_key
JOIN dim_zone AS z
    ON f.pickup_zone_id = z.zone_id
GROUP BY ALL
ORDER BY ALL
"

OPTIMIZED_2="
SELECT
    trip_month,
    provider_name,
    pickup_borough,
    SUM(total_trips) AS total_trips,
    ROUND(SUM(total_base_fare), 2) AS total_base_fare
FROM agg_dashboard_trip_metrics
GROUP BY ALL
ORDER BY ALL
"

run_duckdb() {
    local sql="$1"
    shift
    docker run --rm --entrypoint duckdb \
        --mount "type=bind,source=$PROJECT_DIR,target=/project,readonly" \
        "$DUCKDB_IMAGE" \
        -readonly "$DATABASE_PATH" \
        -cmd "SET threads=2; SET memory_limit='8GB';" \
        "$@" \
        -c "$sql"
}

verify_optimization_1() {
    local sql
    sql="
WITH baseline AS ($BASELINE_1), optimized AS ($OPTIMIZED_1)
SELECT
    baseline.trips,
    baseline.total_base_fare,
    baseline.trips = optimized.trips
        AND baseline.total_base_fare = optimized.total_base_fare AS equivalent
FROM baseline, optimized;
"
    run_duckdb "$sql" -csv -noheader
}

verify_optimization_2() {
    local sql
    sql="
WITH baseline AS ($BASELINE_2),
optimized AS ($OPTIMIZED_2),
differences AS (
    (SELECT * FROM baseline EXCEPT ALL SELECT * FROM optimized)
    UNION ALL
    (SELECT * FROM optimized EXCEPT ALL SELECT * FROM baseline)
),
summary AS (
    SELECT COUNT(*) AS group_count,
           SUM(total_trips) AS total_trips,
           ROUND(SUM(total_base_fare), 2) AS total_base_fare
    FROM baseline
)
SELECT summary.group_count,
       summary.total_trips,
       summary.total_base_fare,
       (SELECT COUNT(*) FROM differences) = 0 AS equivalent
FROM summary;
"
    run_duckdb "$sql" -csv -noheader
}

time_query() {
    local sql="$1"
    local timer_output
    timer_output="$(run_duckdb "COPY ($sql) TO '/dev/null' (FORMAT CSV);" -cmd '.timer on' 2>&1)"
    printf '%s\n' "$timer_output" | awk '/Run Time \(s\): real/ {print $5}' | tail -n 1
}

median() {
    sort -n "$1" | awk '
        { values[NR] = $1 }
        END {
            if (NR % 2) printf "%.3f", values[(NR + 1) / 2]
            else printf "%.3f", (values[NR / 2] + values[NR / 2 + 1]) / 2
        }
    '
}

OPT1_CHECK="$(verify_optimization_1 | tail -n 1)"
OPT2_CHECK="$(verify_optimization_2 | tail -n 1)"

IFS=',' read -r OPT1_TRIPS OPT1_FARE OPT1_EQUIVALENT <<< "$OPT1_CHECK"
IFS=',' read -r OPT2_GROUPS OPT2_TRIPS OPT2_FARE OPT2_EQUIVALENT <<< "$OPT2_CHECK"

if [[ "$OPT1_EQUIVALENT" != "true" || "$OPT2_EQUIVALENT" != "true" ]]; then
    echo "Result-equivalence verification failed; benchmark aborted" >&2
    exit 1
fi

RAW_FILE="$WORK_DIR/raw.csv"
: > "$RAW_FILE"

for run in $(seq 1 "$RUNS"); do
    baseline_seconds="$(time_query "$BASELINE_1")"
    optimized_seconds="$(time_query "$OPTIMIZED_1")"
    printf 'timestamp_range,baseline,%s,%s\n' "$run" "$baseline_seconds" >> "$RAW_FILE"
    printf 'timestamp_range,optimized,%s,%s\n' "$run" "$optimized_seconds" >> "$RAW_FILE"

    baseline_seconds="$(time_query "$BASELINE_2")"
    optimized_seconds="$(time_query "$OPTIMIZED_2")"
    printf 'dashboard_aggregate,baseline,%s,%s\n' "$run" "$baseline_seconds" >> "$RAW_FILE"
    printf 'dashboard_aggregate,optimized,%s,%s\n' "$run" "$optimized_seconds" >> "$RAW_FILE"
done

awk -F, '$1 == "timestamp_range" && $2 == "baseline" {print $4}' "$RAW_FILE" > "$WORK_DIR/opt1_baseline.txt"
awk -F, '$1 == "timestamp_range" && $2 == "optimized" {print $4}' "$RAW_FILE" > "$WORK_DIR/opt1_optimized.txt"
awk -F, '$1 == "dashboard_aggregate" && $2 == "baseline" {print $4}' "$RAW_FILE" > "$WORK_DIR/opt2_baseline.txt"
awk -F, '$1 == "dashboard_aggregate" && $2 == "optimized" {print $4}' "$RAW_FILE" > "$WORK_DIR/opt2_optimized.txt"

OPT1_BASELINE_MEDIAN="$(median "$WORK_DIR/opt1_baseline.txt")"
OPT1_OPTIMIZED_MEDIAN="$(median "$WORK_DIR/opt1_optimized.txt")"
OPT2_BASELINE_MEDIAN="$(median "$WORK_DIR/opt2_baseline.txt")"
OPT2_OPTIMIZED_MEDIAN="$(median "$WORK_DIR/opt2_optimized.txt")"
OPT1_SPEEDUP="$(awk -v b="$OPT1_BASELINE_MEDIAN" -v o="$OPT1_OPTIMIZED_MEDIAN" 'BEGIN {printf "%.1f", b / o}')"
OPT2_SPEEDUP="$(awk -v b="$OPT2_BASELINE_MEDIAN" -v o="$OPT2_OPTIMIZED_MEDIAN" 'BEGIN {printf "%.1f", b / o}')"

{
    echo 'benchmark_date,duckdb_image,threads,memory_limit,optimization,variant,run,seconds,median_seconds,speedup_x,result_equivalent,result_summary'
    while IFS=',' read -r optimization variant run seconds; do
        if [[ "$optimization" == "timestamp_range" ]]; then
            if [[ "$variant" == "baseline" ]]; then median_seconds="$OPT1_BASELINE_MEDIAN"; else median_seconds="$OPT1_OPTIMIZED_MEDIAN"; fi
            speedup="$OPT1_SPEEDUP"
            summary="trips=$OPT1_TRIPS;total_base_fare=$OPT1_FARE"
        else
            if [[ "$variant" == "baseline" ]]; then median_seconds="$OPT2_BASELINE_MEDIAN"; else median_seconds="$OPT2_OPTIMIZED_MEDIAN"; fi
            speedup="$OPT2_SPEEDUP"
            summary="groups=$OPT2_GROUPS;trips=$OPT2_TRIPS;total_base_fare=$OPT2_FARE"
        fi
        printf '%s,%s,2,8GB,%s,%s,%s,%s,%s,%s,true,"%s"\n' \
            "$BENCHMARK_DATE" "$DUCKDB_IMAGE" "$optimization" "$variant" "$run" "$seconds" \
            "$median_seconds" "$speedup" "$summary"
    done < "$RAW_FILE"
} > "$OUTPUT_FILE"

echo "Benchmark evidence: $OUTPUT_FILE"
echo "Timestamp range: median ${OPT1_BASELINE_MEDIAN}s -> ${OPT1_OPTIMIZED_MEDIAN}s (${OPT1_SPEEDUP}x), equivalent=true"
echo "Dashboard aggregate: median ${OPT2_BASELINE_MEDIAN}s -> ${OPT2_OPTIMIZED_MEDIAN}s (${OPT2_SPEEDUP}x), equivalent=true"
