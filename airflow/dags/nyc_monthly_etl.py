import re
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
from airflow.sdk import dag, task, get_current_context, Param

DB = "/warehouse/nyc_mobility.duckdb"
ETL_DIR = Path("/opt/project/etl")


def requested_month():
    context = get_current_context()
    dag_run = context.get("dag_run")
    month = dag_run.conf.get("month") if dag_run and dag_run.conf else None

    # Scheduled runs on the fifth process the previous calendar month.
    if month is None:
        month = context["data_interval_end"].subtract(months=1).strftime("%Y-%m")

    if not isinstance(month, str) or not re.fullmatch(
        r"\d{4}-(0[1-9]|1[0-2])", month
    ):
        raise ValueError(f"Invalid month: {month!r}")

    if not ("2025-01" <= month <= "2026-08"):
        raise ValueError(f"Month outside project range: {month}")

    return month


@dag(
    dag_id="nyc_monthly_etl",
    start_date=datetime(2025, 1, 1),
    schedule="0 6 5 * *",
    end_date=datetime(2026, 9, 6),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=1),
    },
    params={
        "month": Param("2025-01", type="string"),
    },
    tags=["nyc", "mobility", "etl"],
)
def nyc_monthly_etl():

    @task
    def initialize_warehouse():
        sql = (ETL_DIR / "init_warehouse.sql").read_text()

        with duckdb.connect(DB) as con:
            con.execute("BEGIN TRANSACTION")
            try:
                con.execute(sql)
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise

        print("Warehouse initialization completed.")

    @task
    def load_month():
        month = requested_month()
        source = Path(
            f"/data/trip_record_data/fhvhv_tripdata_{month}.parquet"
        )

        if not source.is_file():
            raise FileNotFoundError(source)

        sql = (ETL_DIR / "load_month.sql").read_text()
        sql = sql.replace("{{MONTH}}", month)

        # load_month.sql already manages its own transaction.
        with duckdb.connect(DB) as con:
            con.execute(sql)

        print(f"Monthly ETL completed: {month}")

    @task
    def validate_month():
        month = requested_month()
        source = (
            f"/data/trip_record_data/"
            f"fhvhv_tripdata_{month}.parquet"
        )

        with duckdb.connect(DB, read_only=True) as con:
            raw_count = con.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [source],
            ).fetchone()[0]

            accepted, invalid, missing_keys, bad_sharing, bad_zones = (
                con.execute("""
                    SELECT
                        COUNT(*),
                        COUNT(*) FILTER (
                            WHERE pickup_datetime IS NULL
                               OR dropoff_datetime IS NULL
                               OR dropoff_datetime <= pickup_datetime
                               OR trip_miles < 0
                        ),
                        COUNT(*) FILTER (
                            WHERE dispatching_provider_base_key IS NULL
                               OR originating_provider_base_key IS NULL
                               OR f.ride_features_key IS NULL
                        ),
                        COUNT(*) FILTER (
                            WHERE r.shared_requested = FALSE
                              AND r.shared_matched = TRUE
                        ),
                        COUNT(*) FILTER (
                            WHERE p.zone_id IS NULL
                               OR d.zone_id IS NULL
                        )
                    FROM fact_trips f
                    LEFT JOIN dim_ride_features r
                        ON f.ride_features_key = r.ride_features_key
                    LEFT JOIN dim_zone p
                        ON f.pickup_zone_id = p.zone_id
                    LEFT JOIN dim_zone d
                        ON f.dropoff_zone_id = d.zone_id
                    WHERE f.pickup_datetime >=
                        CAST(? || '-01' AS TIMESTAMP)
                      AND f.pickup_datetime <
                        CAST(? || '-01' AS TIMESTAMP)
                        + INTERVAL '1 MONTH'
                """, [month, month]).fetchone()
            )

            quarantined, missing_reasons = con.execute("""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER (
                        WHERE rejection_reasons IS NULL
                           OR len(rejection_reasons) = 0
                    )
                FROM quarantined_trips
                WHERE source_month = ?
            """, [month]).fetchone()

        difference = raw_count - accepted - quarantined

        print(f"Month: {month}")
        print(f"Raw records: {raw_count:,}")
        print(f"Accepted records: {accepted:,}")
        print(f"Quarantined records: {quarantined:,}")
        print(f"Reconciliation difference: {difference:,}")
        print(f"Invalid accepted records: {invalid:,}")
        print(f"Missing dimension keys: {missing_keys:,}")
        print(f"Inconsistent sharing flags: {bad_sharing:,}")
        print(f"Unmatched zones: {bad_zones:,}")
        print(f"Quarantine records without reasons: {missing_reasons:,}")

        if (
            accepted == 0
            or difference != 0
            or invalid != 0
            or missing_keys != 0
            or bad_sharing != 0
            or bad_zones != 0
            or missing_reasons != 0
        ):
            raise ValueError(f"ETL validation failed for {month}")

        print(f"Validation passed for {month}")

    initialize_warehouse() >> load_month() >> validate_month()


nyc_monthly_etl()
