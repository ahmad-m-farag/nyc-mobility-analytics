#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/artifacts/analytics"
mkdir -p "$OUTPUT_DIR"

for query in "$PROJECT_DIR"/sql/analytics/*.sql; do
    name="$(basename "$query" .sql)"
    docker run --rm --entrypoint duckdb \
        --mount "type=bind,source=$PROJECT_DIR,target=/project" \
        duckdb/duckdb:1.5.6 \
        -readonly /project/warehouse/nyc_mobility.duckdb \
        -c "COPY ($(tr '\n' ' ' < "$query" | sed 's/;[[:space:]]*$//')) TO '/project/artifacts/analytics/$name.csv' (HEADER, DELIMITER ',');"
    echo "Wrote artifacts/analytics/$name.csv"
done
