#!/usr/bin/env python3
"""Download official NYC TLC HVFHV Parquet files for an inclusive month range."""

from __future__ import annotations

import argparse
import calendar
import os
import re
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

MONTH_PATTERN = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
TRIP_DATA_URL = (
    "https://d37ci6vzurychx.cloudfront.net/trip-data/"
    "fhvhv_tripdata_{month}.parquet"
)
ZONE_LOOKUP_URL = (
    "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
)


def parse_month(value: str) -> date:
    match = MONTH_PATTERN.fullmatch(value)
    if not match:
        raise argparse.ArgumentTypeError("month must use YYYY-MM")
    return date(int(match.group(1)), int(match.group(2)), 1)


def month_strings(start: date, end: date):
    current = start
    while current <= end:
        yield current.strftime("%Y-%m")
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)


def download(url: str, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        print(f"SKIP {destination.name}: already exists")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "qeema-nyc-mobility/1.0"},
    )

    try:
        print(f"GET  {url}")
        with urllib.request.urlopen(request, timeout=90) as response:
            with temporary.open("wb") as stream:
                while chunk := response.read(8 * 1024 * 1024):
                    stream.write(chunk)

        if destination.suffix == ".parquet":
            with temporary.open("rb") as stream:
                header = stream.read(4)
                stream.seek(-4, os.SEEK_END)
                footer = stream.read(4)
            if header != b"PAR1" or footer != b"PAR1":
                raise ValueError("download is not a valid Parquet container")

        temporary.replace(destination)
        size_mib = destination.stat().st_size / (1024 * 1024)
        print(f"SAVED {destination} ({size_mib:,.1f} MiB)")
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download official NYC TLC HVFHV monthly Parquet files."
    )
    parser.add_argument("--start", required=True, type=parse_month)
    parser.add_argument("--end", required=True, type=parse_month)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/trip_record_data"),
    )
    parser.add_argument(
        "--zone-lookup",
        type=Path,
        default=Path("/data/taxi_zone_lookup.csv"),
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.start > args.end:
        parser.error("--start must be earlier than or equal to --end")
    if args.start < date(2019, 2, 1):
        parser.error("HVFHV monthly files begin in 2019-02")

    try:
        download(ZONE_LOOKUP_URL, args.zone_lookup, args.force)
        for month in month_strings(args.start, args.end):
            destination = args.output_dir / f"fhvhv_tripdata_{month}.parquet"
            download(TRIP_DATA_URL.format(month=month), destination, args.force)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        parser.exit(1, f"Download failed: {exc}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
