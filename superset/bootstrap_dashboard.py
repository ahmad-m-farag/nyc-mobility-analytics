#!/usr/bin/env python3
"""Create or update the repository-owned NYC Mobility Superset dashboard."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

BASE_URL = os.getenv("SUPERSET_URL", "http://superset:8088").rstrip("/")
USERNAME = os.getenv("SUPERSET_ADMIN_USERNAME", "admin")
PASSWORD = os.getenv("SUPERSET_ADMIN_PASSWORD", "admin")
DATABASE_NAME = "NYC Mobility (read only)"
DASHBOARD_TITLE = "NYC HVFHV Mobility Analytics"
CALCULATED_COLUMNS = {
    "nyc_pickup_borough": {
        "expression": (
            "CASE WHEN pickup_borough IN "
            "('Bronx', 'Brooklyn', 'Manhattan', 'Queens', 'Staten Island') "
            "THEN pickup_borough END"
        ),
        "verbose_name": "NYC pickup borough",
        "description": (
            "Five NYC boroughs only. EWR, N/A, and Unknown remain separate "
            "source categories and are intentionally excluded."
        ),
    },
    "sharing_outcome": {
        "expression": (
            "CASE "
            "WHEN shared_requested = FALSE AND shared_matched = FALSE "
            "THEN 'Sharing not requested' "
            "WHEN shared_requested = TRUE AND shared_matched = TRUE "
            "THEN 'Sharing requested and matched' "
            "WHEN shared_requested = TRUE AND shared_matched = FALSE "
            "THEN 'Sharing requested but not matched' "
            "ELSE 'Other flag combination' END"
        ),
        "verbose_name": "Sharing outcome",
        "description": "Business label derived from the request and match flags.",
    },
}

COLUMN_LABELS = {
    "trip_date": "Pickup date",
    "trip_month": "Pickup month",
    "pickup_hour": "Pickup hour",
    "day_type": "Day type",
    "provider_name": "Provider",
    "pickup_borough": "Pickup area",
    "pickup_zone": "Pickup zone",
    "total_trips": "Accepted trips",
    "total_base_fare": "Base passenger fare (USD)",
}


class SupersetClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.headers: dict[str, str] = {"Content-Type": "application/json"}

    def wait(self) -> None:
        for _ in range(60):
            try:
                response = self.session.get(f"{BASE_URL}/health", timeout=5)
                if response.ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(2)
        raise RuntimeError("Superset did not become healthy")

    def authenticate(self) -> None:
        response = self.session.post(
            f"{BASE_URL}/api/v1/security/login",
            json={
                "username": USERNAME,
                "password": PASSWORD,
                "provider": "db",
                "refresh": True,
            },
            timeout=30,
        )
        response.raise_for_status()
        self.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        csrf = self.session.get(
            f"{BASE_URL}/api/v1/security/csrf_token/",
            headers=self.headers,
            timeout=30,
        )
        csrf.raise_for_status()
        self.headers["X-CSRFToken"] = csrf.json()["result"]

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{BASE_URL}{path}",
            headers=self.headers,
            timeout=90,
            **kwargs,
        )
        if not response.ok:
            raise RuntimeError(
                f"{method} {path} failed ({response.status_code}): {response.text}"
            )
        return response.json() if response.content else {}

    def list_all(self, resource: str) -> list[dict[str, Any]]:
        payload = self.request(
            "GET", f"/api/v1/{resource}/?q=(page:0,page_size:1000)"
        )
        return payload.get("result", [])


def simple_metric(column: str, aggregate: str, label: str) -> dict[str, Any]:
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": column},
        "aggregate": aggregate,
        "sqlExpression": None,
        "hasCustomLabel": True,
        "label": label,
        "optionName": f"metric_{column}_{aggregate.lower()}",
    }


def sql_metric(expression: str, label: str, option_name: str) -> dict[str, Any]:
    return {
        "expressionType": "SQL",
        "column": None,
        "aggregate": None,
        "sqlExpression": expression,
        "hasCustomLabel": True,
        "label": label,
        "optionName": option_name,
    }


def update_dataset_metadata(
    client: SupersetClient, dataset_id: int
) -> None:
    """Keep physical columns and add repository-owned calculated labels."""
    dataset = client.request("GET", f"/api/v1/dataset/{dataset_id}")["result"]
    allowed = {
        "id",
        "column_name",
        "type",
        "advanced_data_type",
        "verbose_name",
        "description",
        "expression",
        "extra",
        "filterable",
        "groupby",
        "is_active",
        "is_dttm",
        "python_date_format",
        "uuid",
    }
    columns: list[dict[str, Any]] = []
    by_name = {column["column_name"]: column for column in dataset["columns"]}

    for column in dataset["columns"]:
        payload = {
            key: value
            for key, value in column.items()
            if key in allowed and value is not None
        }
        if column["column_name"] in COLUMN_LABELS:
            payload["verbose_name"] = COLUMN_LABELS[column["column_name"]]
        columns.append(payload)

    for column_name, definition in CALCULATED_COLUMNS.items():
        existing = by_name.get(column_name, {})
        payload = {
            "column_name": column_name,
            "type": "VARCHAR",
            "verbose_name": definition["verbose_name"],
            "description": definition["description"],
            "expression": definition["expression"],
            "filterable": True,
            "groupby": True,
            "is_active": True,
            "is_dttm": False,
        }
        if existing.get("id") is not None:
            payload["id"] = existing["id"]
        if existing.get("uuid") is not None:
            payload["uuid"] = existing["uuid"]
        columns = [
            column for column in columns if column["column_name"] != column_name
        ]
        columns.append(payload)

    client.request(
        "PUT",
        f"/api/v1/dataset/{dataset_id}",
        json={
            "main_dttm_col": "trip_date",
            "description": (
                "Aggregate at date/hour/provider/zone/sharing grain with "
                "repository-defined business labels."
            ),
            "columns": columns,
        },
    )


def chart_specs(dataset_id: int) -> list[dict[str, Any]]:
    datasource = f"{dataset_id}__table"
    trips = simple_metric("total_trips", "SUM", "Accepted trips")
    fare = simple_metric("total_base_fare", "SUM", "Base fare (USD)")
    fare_billions = sql_metric(
        "SUM(total_base_fare) / 1000000000.0",
        "Base fare (USD billions)",
        "metric_base_fare_usd_billions",
    )
    common = {
        "datasource": datasource,
        "adhoc_filters": [],
        "granularity_sqla": "trip_date",
        "row_limit": 10000,
        "time_range": "No filter",
    }
    five_borough_filter = {
        "clause": "WHERE",
        "comparator": [
            "Bronx",
            "Brooklyn",
            "Manhattan",
            "Queens",
            "Staten Island",
        ],
        "expressionType": "SIMPLE",
        "filterOptionName": "filter_five_nyc_boroughs",
        "fromFormData": True,
        "operator": "IN",
        "sqlExpression": None,
        "subject": "pickup_borough",
    }
    return [
        {
            "name": "Total accepted trips",
            "viz_type": "big_number_total",
            "params": {**common, "viz_type": "big_number_total", "metric": trips},
            "description": "Accepted warehouse trips in the active filter range.",
        },
        {
            "name": "Total base passenger fare (USD billions)",
            "match_names": [
                "Total base passenger fare",
                "Total base passenger fare (USD billions)",
            ],
            "viz_type": "big_number_total",
            "params": {
                **common,
                "viz_type": "big_number_total",
                "metric": fare_billions,
                "y_axis_format": "$,.2f",
            },
            "description": "Base passenger fare before extras and tips, in USD billions.",
        },
        {
            "name": "Monthly trip demand",
            "viz_type": "echarts_timeseries_line",
            "params": {
                **common,
                "viz_type": "echarts_timeseries_line",
                "x_axis": "trip_date",
                "time_grain_sqla": "P1M",
                "metrics": [trips],
                "groupby": [],
                "show_legend": False,
                "legendOrientation": "top",
                "x_axis_time_format": "%b %Y",
                "tooltipTimeFormat": "%B %Y",
                "y_axis_format": ",.4s",
                "x_axis_title": "Pickup month",
                "y_axis_title": "Accepted trips",
                "x_axis_title_margin": 35,
                "y_axis_title_margin": 65,
                "markerEnabled": True,
                "markerSize": 5,
                "rich_tooltip": True,
                "truncateYAxis": False,
            },
            "description": "Total accepted trips by pickup month.",
        },
        {
            "name": "Provider comparison",
            "viz_type": "echarts_timeseries_bar",
            "params": {
                **common,
                "viz_type": "echarts_timeseries_bar",
                "x_axis": "provider_name",
                "metrics": [trips],
                "groupby": [],
                "orientation": "horizontal",
                "show_legend": False,
                # Superset 6 clips outside-end labels at the responsive panel
                # edge. The labelled value axis and tooltip retain the values
                # without displaying a misleading truncated number.
                "show_value": False,
                "y_axis_format": ",.4s",
                "x_axis_title": "",
                "y_axis_title": "Accepted trips",
                "x_axis_title_margin": 45,
                "y_axis_title_margin": 35,
                "truncateXAxis": False,
            },
            "description": "Trip volume by dispatching provider.",
        },
        {
            "name": "Hourly demand by day type",
            "viz_type": "echarts_timeseries_bar",
            "params": {
                **common,
                "viz_type": "echarts_timeseries_bar",
                "x_axis": "pickup_hour",
                "metrics": [trips],
                "groupby": ["day_type"],
                "show_legend": True,
                "legendOrientation": "top",
                "stack": None,
                "x_axis_sort": "pickup_hour",
                "x_axis_sort_asc": True,
                "xAxisLabelInterval": "0",
                "y_axis_format": ",.4s",
                "x_axis_title": "Pickup hour (0-23)",
                "y_axis_title": "Accepted trips",
                "x_axis_title_margin": 35,
                "y_axis_title_margin": 65,
            },
            "description": "Accepted trips by pickup hour for weekdays and weekends.",
        },
        {
            "name": "Trips by NYC pickup borough",
            "match_names": [
                "Trips by pickup borough",
                "Trips by NYC pickup borough",
            ],
            "viz_type": "echarts_timeseries_bar",
            "params": {
                **common,
                "viz_type": "echarts_timeseries_bar",
                "adhoc_filters": [five_borough_filter],
                "x_axis": "nyc_pickup_borough",
                "metrics": [trips],
                "groupby": ["provider_name"],
                "show_legend": True,
                "legendOrientation": "top",
                "stack": None,
                "x_axis_sort": "nyc_pickup_borough",
                "x_axis_sort_asc": True,
                "xAxisLabelInterval": "0",
                "xAxisLabelRotation": 0,
                "truncateXAxis": False,
                "y_axis_format": ",.4s",
                "x_axis_title": "NYC pickup borough",
                "y_axis_title": "Accepted trips",
                "x_axis_title_margin": 35,
                "y_axis_title_margin": 65,
            },
            "description": (
                "Uber and Lyft trip volume for the five NYC boroughs. "
                "EWR, N/A, and Unknown are not classified as NYC boroughs."
            ),
        },
        {
            "name": "Top pickup zones",
            "viz_type": "table",
            "params": {
                **common,
                "viz_type": "table",
                "groupby": ["pickup_borough", "pickup_zone"],
                "metrics": [trips, fare],
                "order_by_cols": ["[\"Trips\", false]"],
                "page_length": 10,
                "include_search": True,
                "table_filter": True,
                "column_config": {
                    "Accepted trips": {"d3NumberFormat": ",.4s"},
                    "Base fare (USD)": {"d3NumberFormat": "$,.4s"},
                },
            },
            "description": "Highest-volume pickup zones in the active filter range.",
        },
        {
            "name": "Shared ride outcomes",
            "viz_type": "echarts_timeseries_bar",
            "params": {
                **common,
                "viz_type": "echarts_timeseries_bar",
                "x_axis": "sharing_outcome",
                "metrics": [trips],
                "groupby": [],
                "orientation": "horizontal",
                "show_legend": False,
                "show_value": True,
                "stack": None,
                "x_axis_sort": "Accepted trips",
                "x_axis_sort_asc": False,
                "xAxisLabelInterval": "0",
                "truncateXAxis": False,
                "y_axis_format": ",.4s",
                "x_axis_title": "",
                "y_axis_title": "Accepted trips",
                "x_axis_title_margin": 130,
                "y_axis_title_margin": 35,
            },
            "description": "Business-readable outcome derived from request and match flags.",
        },
    ]


def native_filters(dataset_id: int) -> list[dict[str, Any]]:
    filters = []
    for suffix, name, column in (
        ("provider", "Provider", "provider_name"),
        ("borough", "Pickup borough", "pickup_borough"),
    ):
        filters.append(
            {
                "id": f"NATIVE_FILTER-{suffix}",
                "name": name,
                "filterType": "filter_select",
                "targets": [{"datasetId": dataset_id, "column": {"name": column}}],
                "defaultDataMask": {
                    "extraFormData": {},
                    "filterState": {},
                    "ownState": {},
                },
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                "controlValues": {
                    "enableEmptyFilter": False,
                    "multiSelect": True,
                    "searchAllOptions": False,
                    "inverseSelection": False,
                },
                "type": "NATIVE_FILTER",
            }
        )
    filters.insert(
        0,
        {
            "id": "NATIVE_FILTER-trip-date",
            "name": "Pickup date",
            "filterType": "filter_time",
            # Superset time-range filters are global. Each chart resolves the
            # range through its dataset's configured temporal column.
            "targets": [{}],
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "controlValues": {"enableEmptyFilter": False},
            "type": "NATIVE_FILTER",
        },
    )
    return filters


def dashboard_layout(charts: list[tuple[int, str]]) -> str:
    layout: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
        "GRID_ID": {"id": "GRID_ID", "type": "GRID", "children": []},
    }
    widths = [6, 6, 12, 5, 7, 12, 12, 12]
    heights = [16, 16, 42, 36, 36, 42, 46, 42]
    row_id = ""
    current_width = 0
    row_number = 0
    for index, (chart_id, chart_name) in enumerate(charts):
        width = widths[index]
        if not row_id or current_width + width > 12:
            row_number += 1
            row_id = f"ROW-{row_number}"
            layout["GRID_ID"]["children"].append(row_id)
            layout[row_id] = {
                "id": row_id,
                "type": "ROW",
                "children": [],
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
                "parents": ["ROOT_ID", "GRID_ID"],
            }
            current_width = 0
        chart_key = f"CHART-{chart_id}"
        layout[row_id]["children"].append(chart_key)
        layout[chart_key] = {
            "id": chart_key,
            "type": "CHART",
            "children": [],
            "meta": {
                "chartId": chart_id,
                "height": heights[index],
                "width": width,
                "sliceName": chart_name,
            },
            "parents": ["ROOT_ID", "GRID_ID", row_id],
        }
        current_width += width
    return json.dumps(layout)


def main() -> None:
    client = SupersetClient()
    client.wait()
    client.authenticate()

    database_payload = {
        "database_name": DATABASE_NAME,
        "sqlalchemy_uri": "duckdb:////warehouse/nyc_mobility.duckdb",
        "configuration_method": "sqlalchemy_form",
        "expose_in_sqllab": True,
        "allow_dml": False,
        "allow_ctas": False,
        "allow_cvas": False,
        "extra": json.dumps(
            {"engine_params": {"connect_args": {"read_only": True}}}
        ),
    }
    database = next(
        (
            row
            for row in client.list_all("database")
            if row.get("database_name") == DATABASE_NAME
        ),
        None,
    )
    if database:
        database_id = database["id"]
        client.request("PUT", f"/api/v1/database/{database_id}", json=database_payload)
    else:
        database_id = client.request(
            "POST", "/api/v1/database/", json=database_payload
        )["id"]

    dataset = next(
        (
            row
            for row in client.list_all("dataset")
            if row.get("table_name") == "agg_dashboard_trip_metrics"
        ),
        None,
    )
    if dataset:
        dataset_id = dataset["id"]
    else:
        dataset_id = client.request(
            "POST",
            "/api/v1/dataset/",
            json={
                "database": database_id,
                "schema": "main",
                "table_name": "agg_dashboard_trip_metrics",
            },
        )["id"]
    update_dataset_metadata(client, dataset_id)

    dashboard_payload = {
        "dashboard_title": DASHBOARD_TITLE,
        "slug": "nyc-hvfhv-mobility-analytics",
        "published": True,
        "json_metadata": json.dumps(
            {
                "timed_refresh_immune_slices": [],
                "expanded_slices": {},
                "refresh_frequency": 0,
                "default_filters": "{}",
                "native_filter_configuration": native_filters(dataset_id),
                "color_scheme": "supersetColors",
                "cross_filters_enabled": True,
            }
        ),
    }
    dashboard = next(
        (
            row
            for row in client.list_all("dashboard")
            if row.get("dashboard_title") == DASHBOARD_TITLE
        ),
        None,
    )
    if dashboard:
        dashboard_id = dashboard["id"]
        client.request(
            "PUT", f"/api/v1/dashboard/{dashboard_id}", json=dashboard_payload
        )
    else:
        dashboard_id = client.request(
            "POST", "/api/v1/dashboard/", json=dashboard_payload
        )["id"]

    existing_charts = client.list_all("chart")
    dashboard_charts: list[tuple[int, str]] = []
    for spec in chart_specs(dataset_id):
        payload = {
            "slice_name": spec["name"],
            "description": spec["description"],
            "viz_type": spec["viz_type"],
            "params": json.dumps(spec["params"]),
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "dashboards": [dashboard_id],
        }
        existing = next(
            (
                row
                for row in existing_charts
                if row.get("slice_name")
                in spec.get("match_names", [spec["name"]])
            ),
            None,
        )
        if existing:
            chart_id = existing["id"]
            client.request("PUT", f"/api/v1/chart/{chart_id}", json=payload)
        else:
            chart_id = client.request(
                "POST", "/api/v1/chart/", json=payload
            )["id"]
        dashboard_charts.append((chart_id, spec["name"]))

    dashboard_payload["position_json"] = dashboard_layout(dashboard_charts)
    client.request(
        "PUT", f"/api/v1/dashboard/{dashboard_id}", json=dashboard_payload
    )
    print(
        f"Dashboard ready: {BASE_URL}/superset/dashboard/"
        "nyc-hvfhv-mobility-analytics/"
    )


if __name__ == "__main__":
    main()
