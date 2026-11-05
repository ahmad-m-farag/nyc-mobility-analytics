# Windows deployment on a ThinkPad T470p

## Recommended setup

1. Enable CPU virtualization in BIOS.
2. Install Docker Desktop and select the WSL 2 backend with Linux containers.
3. Install an Ubuntu WSL distribution.
4. Clone the repository under the WSL filesystem, for example `~/projects/nyc-mobility`, instead of `/mnt/c/...`. Linux bind mounts are substantially faster there.
5. In Docker Desktop, allocate at least 12 GB RAM, four CPUs, and 50 GB disk. The laptop's 32 GB RAM is sufficient.
6. Copy `.env.example` to `.env` and replace the placeholders.

## Commands from Ubuntu/WSL

Build the images, then start the required services without running `superset-bootstrap`:

```bash
docker compose build
docker compose up -d postgres airflow superset-init superset
```

Download the required inclusive month range and initialize the warehouse:

```bash
docker compose --profile tools run --rm downloader --start 2025-01 --end 2026-08
docker compose --profile tools run --rm warehouse-init
```

Load data through Airflow. To process one selected month, replace `2025-01` as needed and run:

```bash
docker compose exec airflow airflow dags trigger nyc_monthly_etl \
  --conf '{"month":"2025-01"}'
docker compose exec airflow airflow dags list-runs nyc_monthly_etl
```

Wait until the DAG run and its `initialize_warehouse`, `load_month`, and `validate_month` tasks report `success`. For multiple months, trigger `nyc_historical_backfill` in the Airflow UI with the required `start_month` and `end_month` values and wait for every monthly run to succeed.

Create the dashboard aggregates, then run the one-shot dashboard bootstrap:

```bash
docker compose --profile tools run --rm warehouse-optimize
docker compose up --force-recreate --no-deps superset-bootstrap
```

Do not run `superset-bootstrap` before `warehouse-optimize`; the bootstrap requires `agg_dashboard_trip_metrics` and `agg_route_metrics`. After the bootstrap exits successfully, open:

- Airflow: [http://localhost:8080](http://localhost:8080)
- Superset dashboard: [http://localhost:8088/superset/dashboard/nyc-hvfhv-mobility-analytics/](http://localhost:8088/superset/dashboard/nyc-hvfhv-mobility-analytics/)

## Resource behavior

- ETL and aggregate SQL cap DuckDB at 8 GB and two threads.
- `max_active_runs=1` prevents concurrent DuckDB writers.
- PostgreSQL and Superset metadata volumes are small relative to the warehouse.
- Keep the laptop connected to power and prevent sleep during a full historical load.

## Troubleshooting

- If Docker cannot mount the project, verify Docker Desktop WSL integration for the selected distribution.
- If port 8080 or 8088 is occupied, change only the host side of the mapping in `docker-compose.yml`.
- If a load runs out of disk, remove stopped disposable containers and old image layers; do not delete `warehouse/nyc_mobility.duckdb` or the Parquet source directory.
- If Superset starts before the dashboard appears, inspect `docker compose logs superset-bootstrap` and rerun the one-shot service.
- If a browser cannot reach localhost, use `http://127.0.0.1:8080` or `http://127.0.0.1:8088`.
