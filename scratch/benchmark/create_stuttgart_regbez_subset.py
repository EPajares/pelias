#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Stuttgart Regierungsbezirk benchmark subset via spatial intersection"
    )
    parser.add_argument(
        "--comparison-csv",
        default="data/benchmark/comparison_results.csv",
        help="Input comparison CSV containing google_lat/google_lon",
    )
    parser.add_argument(
        "--wof-sqlite",
        default=(
            "tools/pelias-germany-no-oa/pelias-docker/projects/stuttgart-regbez/"
            "data/whosonfirst/sqlite/whosonfirst-data-admin-de-latest.db"
        ),
        help="WOF sqlite DB containing geojson table",
    )
    parser.add_argument(
        "--wof-id",
        type=int,
        default=404227549,
        help="WOF ID of Stuttgart Regierungsbezirk (macrocounty)",
    )
    parser.add_argument(
        "--output-comparison-csv",
        default="data/benchmark/comparison_results_stuttgart_regbez.csv",
        help="Filtered comparison CSV output",
    )
    parser.add_argument(
        "--output-query-csv",
        default="data/benchmark/geocoding_unique_stuttgart_regbez.csv",
        help="Unique query CSV output for internal geocoder",
    )
    return parser.parse_args()


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False

    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]

        intersects = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) if (yj - yi) != 0 else 1e-30) + xi
        )
        if intersects:
            inside = not inside
        j = i

    return inside


def point_in_polygon(lon: float, lat: float, polygon: list[list[list[float]]]) -> bool:
    if not polygon:
        return False

    exterior = polygon[0]
    if not point_in_ring(lon, lat, exterior):
        return False

    for hole in polygon[1:]:
        if point_in_ring(lon, lat, hole):
            return False

    return True


def point_in_geometry(lon: float, lat: float, geometry: dict[str, Any]) -> bool:
    geometry_type = geometry.get("type")
    coords = geometry.get("coordinates")

    if geometry_type == "Polygon":
        return point_in_polygon(lon, lat, coords)

    if geometry_type == "MultiPolygon":
        for polygon in coords:
            if point_in_polygon(lon, lat, polygon):
                return True
        return False

    return False


def load_wof_geometry(wof_sqlite: Path, wof_id: int) -> dict[str, Any]:
    connection = sqlite3.connect(str(wof_sqlite))
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT body FROM geojson WHERE id=?", (wof_id,))
        row = cursor.fetchone()
        if not row:
            raise SystemExit(f"No geojson entry found for WOF id={wof_id}")

        body = json.loads(row[0])
        geometry = body.get("geometry")
        if not isinstance(geometry, dict):
            raise SystemExit(f"No geometry found for WOF id={wof_id}")

        geometry_type = geometry.get("type")
        if geometry_type not in {"Polygon", "MultiPolygon"}:
            raise SystemExit(f"Unsupported geometry type for WOF id={wof_id}: {geometry_type}")

        return geometry
    finally:
        connection.close()


def main() -> int:
    args = parse_args()

    comparison_path = Path(args.comparison_csv)
    wof_sqlite_path = Path(args.wof_sqlite)
    output_comparison = Path(args.output_comparison_csv)
    output_query = Path(args.output_query_csv)

    geometry = load_wof_geometry(wof_sqlite_path, args.wof_id)

    with comparison_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not fieldnames:
        raise SystemExit("Input comparison CSV has no headers")

    filtered_rows: list[dict[str, Any]] = []
    missing_google_coords = 0

    for row in rows:
        lat = to_float(row.get("google_lat"))
        lon = to_float(row.get("google_lon"))
        if lat is None or lon is None:
            missing_google_coords += 1
            continue

        if point_in_geometry(lon, lat, geometry):
            filtered_rows.append(row)

    output_comparison.parent.mkdir(parents=True, exist_ok=True)
    with output_comparison.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)

    seen_queries: set[str] = set()
    query_rows: list[dict[str, str]] = []

    for row in filtered_rows:
        query = (row.get("query_text") or "").strip()
        if not query or query in seen_queries:
            continue
        seen_queries.add(query)
        query_rows.append({"geocode_input_text": query})

    output_query.parent.mkdir(parents=True, exist_ok=True)
    with output_query.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["geocode_input_text"])
        writer.writeheader()
        writer.writerows(query_rows)

    print(f"wof_id={args.wof_id}")
    print(f"input_rows={len(rows)}")
    print(f"missing_google_coords={missing_google_coords}")
    print(f"inside_regbez_rows={len(filtered_rows)}")
    print(f"unique_queries={len(query_rows)}")
    print(f"output_comparison={output_comparison}")
    print(f"output_query={output_query}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
