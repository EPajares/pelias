#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass
class GoogleResult:
    query_text: str
    status: str
    lat: float | None
    lon: float | None
    formatted_address: str | None
    place_id: str | None
    location_type: str | None
    error: str | None
    requested_at: str

    def to_json(self) -> dict[str, Any]:
        return {
            "query_text": self.query_text,
            "status": self.status,
            "lat": self.lat,
            "lon": self.lon,
            "formatted_address": self.formatted_address,
            "place_id": self.place_id,
            "location_type": self.location_type,
            "error": self.error,
            "requested_at": self.requested_at,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one-time Google geocoding benchmark against existing internal geocoding outputs in CSV."
    )
    parser.add_argument(
        "--input-csv",
        default="data/geocoding.csv",
        help="Path to input CSV with geocode_input_text and internal geocode columns.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/benchmark",
        help="Directory for output artifacts.",
    )
    parser.add_argument(
        "--google-api-key",
        default=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        help="Google Maps API key. Defaults to GOOGLE_MAPS_API_KEY env var.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.2,
        help="Delay between uncached Google requests.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="HTTP timeout for Google request.",
    )
    parser.add_argument(
        "--max-unique-queries",
        type=int,
        default=0,
        help="Optional safety cap. 0 = no cap (process all unique queries).",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_m * c


def call_google_geocode(query_text: str, api_key: str, timeout_seconds: int) -> GoogleResult:
    params = urlencode({"address": query_text, "key": api_key})
    req = Request(f"{GOOGLE_GEOCODE_URL}?{params}", method="GET")
    requested_at = now_iso()

    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return GoogleResult(
            query_text=query_text,
            status="REQUEST_ERROR",
            lat=None,
            lon=None,
            formatted_address=None,
            place_id=None,
            location_type=None,
            error=str(exc),
            requested_at=requested_at,
        )

    status = payload.get("status", "UNKNOWN")
    results = payload.get("results", []) or []

    if status != "OK" or not results:
        return GoogleResult(
            query_text=query_text,
            status=status,
            lat=None,
            lon=None,
            formatted_address=None,
            place_id=None,
            location_type=None,
            error=payload.get("error_message"),
            requested_at=requested_at,
        )

    first = results[0]
    geometry = first.get("geometry", {})
    location = geometry.get("location", {})

    return GoogleResult(
        query_text=query_text,
        status=status,
        lat=location.get("lat"),
        lon=location.get("lng"),
        formatted_address=first.get("formatted_address"),
        place_id=first.get("place_id"),
        location_type=geometry.get("location_type"),
        error=None,
        requested_at=requested_at,
    )


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        return list(reader)


def load_google_cache(cache_path: Path) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    if not cache_path.exists():
        return cache

    with cache_path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            query_text = item.get("query_text")
            if isinstance(query_text, str) and query_text:
                cache[query_text] = item
    return cache


def append_cache_entry(cache_path: Path, entry: dict[str, Any]) -> None:
    with cache_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values_sorted = sorted(values)
    idx = int(math.ceil((p / 100.0) * len(values_sorted))) - 1
    idx = max(0, min(idx, len(values_sorted) - 1))
    return values_sorted[idx]


def write_comparison_csv(output_path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    fieldnames = [
        "fid",
        "query_text",
        "internal_lat",
        "internal_lon",
        "internal_confidence",
        "internal_match_type",
        "google_status",
        "google_lat",
        "google_lon",
        "google_formatted_address",
        "google_place_id",
        "google_location_type",
        "distance_m",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_md(
    output_path: Path,
    total_rows: int,
    unique_queries: int,
    cached_before: int,
    newly_requested: int,
    google_ok_unique: int,
    rows_with_internal_coords: int,
    rows_with_google_coords: int,
    rows_with_both: int,
    median_distance: float | None,
    p90_distance: float | None,
    within_50m: int,
    within_100m: int,
    within_250m: int,
) -> None:
    def fmt(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.2f}"

    with output_path.open("w", encoding="utf-8") as fp:
        fp.write("# Geocoding Benchmark Summary\n\n")
        fp.write(f"Generated: {now_iso()}\n\n")
        fp.write("## Run Stats\n\n")
        fp.write(f"- Total rows: {total_rows}\n")
        fp.write(f"- Unique query texts: {unique_queries}\n")
        fp.write(f"- Cached unique results before run: {cached_before}\n")
        fp.write(f"- Newly requested from Google: {newly_requested}\n")
        fp.write(f"- Unique Google status=OK: {google_ok_unique}\n\n")

        fp.write("## Coverage\n\n")
        fp.write(f"- Rows with internal coordinates: {rows_with_internal_coords}\n")
        fp.write(f"- Rows with Google coordinates: {rows_with_google_coords}\n")
        fp.write(f"- Rows with both coordinates: {rows_with_both}\n\n")

        fp.write("## Distance Metrics (rows with both coordinates)\n\n")
        fp.write(f"- Median distance (m): {fmt(median_distance)}\n")
        fp.write(f"- P90 distance (m): {fmt(p90_distance)}\n")
        fp.write(f"- Rows within 50m: {within_50m}\n")
        fp.write(f"- Rows within 100m: {within_100m}\n")
        fp.write(f"- Rows within 250m: {within_250m}\n")


def main() -> int:
    args = parse_args()

    if not args.google_api_key:
        print("ERROR: Missing Google API key. Set --google-api-key or GOOGLE_MAPS_API_KEY.", file=sys.stderr)
        return 1

    csv_path = Path(args.input_csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        print(f"ERROR: Input CSV not found: {csv_path}", file=sys.stderr)
        return 1

    rows = read_csv_rows(csv_path)
    total_rows = len(rows)

    unique_queries: list[str] = []
    seen: set[str] = set()
    for row in rows:
        query_text = (row.get("geocode_input_text") or "").strip()
        if not query_text:
            continue
        if query_text not in seen:
            seen.add(query_text)
            unique_queries.append(query_text)

    if args.max_unique_queries > 0:
        unique_queries = unique_queries[: args.max_unique_queries]

    cache_path = output_dir / "google_cache.jsonl"
    cache = load_google_cache(cache_path)
    cached_before = len(cache)

    pending = [q for q in unique_queries if q not in cache]
    newly_requested = 0

    print(f"Total rows: {total_rows}")
    print(f"Unique queries to evaluate: {len(unique_queries)}")
    print(f"Cached before run: {cached_before}")
    print(f"Pending Google requests: {len(pending)}")

    for idx, query_text in enumerate(pending, start=1):
        result = call_google_geocode(query_text, args.google_api_key, args.timeout_seconds)
        entry = result.to_json()
        cache[query_text] = entry
        append_cache_entry(cache_path, entry)
        newly_requested += 1

        if idx % 50 == 0 or idx == len(pending):
            print(f"Google progress: {idx}/{len(pending)}")

        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    comparison_rows: list[dict[str, Any]] = []
    distances: list[float] = []
    rows_with_internal_coords = 0
    rows_with_google_coords = 0
    rows_with_both = 0
    within_50m = 0
    within_100m = 0
    within_250m = 0

    for row in rows:
        query_text = (row.get("geocode_input_text") or "").strip()
        google_item = cache.get(query_text, {})

        internal_lat = to_float(row.get("geocode_latitude"))
        internal_lon = to_float(row.get("geocode_longitude"))
        google_lat = google_item.get("lat")
        google_lon = google_item.get("lon")

        if internal_lat is not None and internal_lon is not None:
            rows_with_internal_coords += 1
        if isinstance(google_lat, (int, float)) and isinstance(google_lon, (int, float)):
            rows_with_google_coords += 1

        distance_m: float | None = None
        if (
            internal_lat is not None
            and internal_lon is not None
            and isinstance(google_lat, (int, float))
            and isinstance(google_lon, (int, float))
        ):
            rows_with_both += 1
            distance_m = haversine_meters(internal_lat, internal_lon, float(google_lat), float(google_lon))
            distances.append(distance_m)
            if distance_m <= 50:
                within_50m += 1
            if distance_m <= 100:
                within_100m += 1
            if distance_m <= 250:
                within_250m += 1

        comparison_rows.append(
            {
                "fid": row.get("fid"),
                "query_text": query_text,
                "internal_lat": internal_lat,
                "internal_lon": internal_lon,
                "internal_confidence": row.get("geocode_confidence"),
                "internal_match_type": row.get("geocode_match_type"),
                "google_status": google_item.get("status"),
                "google_lat": google_lat,
                "google_lon": google_lon,
                "google_formatted_address": google_item.get("formatted_address"),
                "google_place_id": google_item.get("place_id"),
                "google_location_type": google_item.get("location_type"),
                "distance_m": None if distance_m is None else round(distance_m, 3),
            }
        )

    google_ok_unique = sum(1 for q in unique_queries if cache.get(q, {}).get("status") == "OK")

    median_distance = statistics.median(distances) if distances else None
    p90_distance = percentile(distances, 90)

    comparison_csv = output_dir / "comparison_results.csv"
    write_comparison_csv(comparison_csv, comparison_rows)

    summary_md = output_dir / "summary_metrics.md"
    write_summary_md(
        output_path=summary_md,
        total_rows=total_rows,
        unique_queries=len(unique_queries),
        cached_before=cached_before,
        newly_requested=newly_requested,
        google_ok_unique=google_ok_unique,
        rows_with_internal_coords=rows_with_internal_coords,
        rows_with_google_coords=rows_with_google_coords,
        rows_with_both=rows_with_both,
        median_distance=median_distance,
        p90_distance=p90_distance,
        within_50m=within_50m,
        within_100m=within_100m,
        within_250m=within_250m,
    )

    print("\nBenchmark run completed.")
    print(f"- Cache file: {cache_path}")
    print(f"- Comparison CSV: {comparison_csv}")
    print(f"- Summary markdown: {summary_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
