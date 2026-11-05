#!/bin/bash
set -euo pipefail

MONTH="${1:-}"

if [[ ! "$MONTH" =~ ^[0-9]{4}-(0[1-9]|1[0-2])$ ]]; then
    echo "Usage: ./etl/load_month.sh YYYY-MM"
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FILE="$PROJECT_DIR/data/trip_record_data/fhvhv_tripdata_$MONTH.parquet"

if [[ ! -f "$FILE" ]]; then
    echo "ERROR: Parquet file not found for $MONTH"
    exit 1
fi

echo "Starting ETL for $MONTH"

sed "s/{{MONTH}}/$MONTH/g" "$PROJECT_DIR/etl/load_month.sql" | \
docker run --rm -i \
    --entrypoint duckdb \
    --mount "type=bind,source=$PROJECT_DIR/data,target=/data,readonly" \
    --mount "type=bind,source=$PROJECT_DIR/warehouse,target=/warehouse" \
    duckdb/duckdb:1.5.6 \
    -bail /warehouse/nyc_mobility.duckdb

echo "ETL command completed for $MONTH"
