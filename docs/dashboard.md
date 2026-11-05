# Superset dashboard guide

## Dashboard

`NYC HVFHV Mobility Analytics` is created by `superset/bootstrap_dashboard.py`; it does not depend on an unpublished Docker volume. The script is idempotent and updates existing assets by name.

The database is mounted read-only and configured with `connect_args.read_only=true`. Superset cannot write to the production DuckDB file.

## Native filters

- Pickup date
- Dispatching provider
- Pickup borough

The filters target the common aggregate dataset and apply across the dashboard.

## Charts and KPI definitions

| Chart | Definition |
|---|---|
| Total accepted trips | Sum of `total_trips` after active filters |
| Total base passenger fare | Sum of base fare before tolls, taxes, surcharges, tips, and driver pay |
| Monthly trip demand | Total accepted trips by pickup month |
| Provider comparison | Trips by dispatching provider, with exact values in tooltips |
| Hourly demand by day type | Trips by pickup hour and weekday/weekend classification |
| Trips by NYC pickup borough | Grouped Uber/Lyft comparison for the five NYC boroughs; EWR, N/A, and Unknown are excluded rather than misclassified |
| Top pickup zones | Ranked zone table with trips and base fare |
| Shared ride outcomes | Horizontal bars with business labels for not requested, requested and matched, and requested but not matched |

## Recreate or update

```bash
docker compose up -d superset-init superset
docker compose up --force-recreate --no-deps superset-bootstrap
```

Open [http://localhost:8088/superset/dashboard/nyc-hvfhv-mobility-analytics/](http://localhost:8088/superset/dashboard/nyc-hvfhv-mobility-analytics/).

## Verified state

On 5 November 2026, the bootstrap completed successfully against Superset 6.0.0. Visual inspection confirmed eight rendered charts, three filters, the 412M trip KPI, the $11.2B base-fare KPI, and the top-zone results led by LaGuardia and JFK airports.

## Refresh after ETL

Run the aggregate refresh before reloading the dashboard assets:

```bash
docker compose --profile tools run --rm warehouse-optimize
docker compose up --force-recreate --no-deps superset-bootstrap
```
