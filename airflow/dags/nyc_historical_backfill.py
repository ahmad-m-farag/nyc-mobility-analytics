import re
from datetime import datetime, timedelta

from airflow.sdk import dag, Param
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import (
    PythonOperator,
    BranchPythonOperator,
)
from airflow.providers.standard.operators.trigger_dagrun import (
    TriggerDagRunOperator,
)

FIRST_MONTH = "2025-01"
LAST_MONTH = "2026-08"


def validate_range(**context):
    start = context["params"]["start_month"]
    end = context["params"]["end_month"]

    pattern = r"\d{4}-(0[1-9]|1[0-2])"

    if not all(
        isinstance(value, str) and re.fullmatch(pattern, value)
        for value in (start, end)
    ):
        raise ValueError("Months must use YYYY-MM format.")

    if not (FIRST_MONTH <= start <= end <= LAST_MONTH):
        raise ValueError(
            f"Invalid range: {start} to {end}. "
            f"Allowed: {FIRST_MONTH} to {LAST_MONTH}."
        )

    print(f"Backfill range: {start} through {end}")


def choose_month(month, **context):
    start = context["params"]["start_month"]
    end = context["params"]["end_month"]
    suffix = month.replace("-", "_")

    if start <= month <= end:
        return f"load_{suffix}"

    return f"skip_{suffix}"


@dag(
    dag_id="nyc_historical_backfill",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=1),
    },
    params={
        "start_month": Param(
            "2025-03",
            type="string",
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
            title="Start Month",
        ),
        "end_month": Param(
            "2026-08",
            type="string",
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
            title="End Month",
        ),
    },
    tags=["nyc", "mobility", "backfill"],
)
def nyc_historical_backfill():

    previous = PythonOperator(
        task_id="validate_range",
        python_callable=validate_range,
    )

    for year in (2025, 2026):
        for number in range(1, 13):
            month = f"{year}-{number:02d}"

            if not FIRST_MONTH <= month <= LAST_MONTH:
                continue

            suffix = month.replace("-", "_")

            branch = BranchPythonOperator(
                task_id=f"choose_{suffix}",
                python_callable=choose_month,
                op_kwargs={"month": month},
            )

            load = TriggerDagRunOperator(
                task_id=f"load_{suffix}",
                trigger_dag_id="nyc_monthly_etl",
                conf={"month": month},
                wait_for_completion=True,
                poke_interval=30,
                allowed_states=["success"],
                failed_states=["failed"],
            )

            skip = EmptyOperator(
                task_id=f"skip_{suffix}",
            )

            join = EmptyOperator(
                task_id=f"finish_{suffix}",
                trigger_rule="none_failed_min_one_success",
            )

            previous >> branch
            branch >> [load, skip]
            [load, skip] >> join

            previous = join


nyc_historical_backfill()
