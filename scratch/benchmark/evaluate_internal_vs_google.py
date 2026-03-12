#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate internal geocoding output against cached Google baseline")
    parser.add_argument("--input-csv", required=True, help="CSV with query_text and internal lat/lon columns")
    parser.add_argument("--google-cache", default="data/benchmark/google_cache.jsonl")
    parser.add_argument("--query-col", default="geocode_input_text")
    parser.add_argument("--lat-col", default="internal_service_latitude")
    parser.add_argument("--lon-col", default="internal_service_longitude")
    parser.add_argument("--label", default="internal")
    parser.add_argument("--output-md", required=True)
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


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2.0) ** 2
    return radius_m * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    idx = int(math.ceil((p / 100.0) * len(values))) - 1
    idx = max(0, min(idx, len(values) - 1))
    return values[idx]


def load_google_cache(path: Path) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            query = item.get("query_text")
            if isinstance(query, str) and query:
                cache[query] = item
    return cache


def summarize_slice(rows: list[tuple[str, float]]) -> dict[str, Any]:
    dists = [d for _, d in rows]
    if not dists:
        return {
            "count": 0,
            "median": None,
            "p90": None,
            "within_50": 0,
            "within_100": 0,
            "within_250": 0,
        }
    return {
        "count": len(dists),
        "median": statistics.median(dists),
        "p90": percentile(dists, 90),
        "within_50": sum(1 for d in dists if d <= 50),
        "within_100": sum(1 for d in dists if d <= 100),
        "within_250": sum(1 for d in dists if d <= 250),
    }


def fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.2f}"


def pct(a: int, b: int) -> str:
    return "n/a" if b == 0 else f"{(a / b * 100):.2f}%"


def main() -> int:
    args = parse_args()
    in_path = Path(args.input_csv)
    cache_path = Path(args.google_cache)
    out_path = Path(args.output_md)

    cache = load_google_cache(cache_path)

    distances: list[tuple[str, float]] = []
    with in_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        query = (row.get(args.query_col) or "").strip()
        g = cache.get(query, {})

        glat = to_float(g.get("lat"))
        glon = to_float(g.get("lon"))
        ilat = to_float(row.get(args.lat_col))
        ilon = to_float(row.get(args.lon_col))

        if glat is None or glon is None or ilat is None or ilon is None:
            continue

        d = haversine_m(ilat, ilon, glat, glon)
        distances.append((query, d))

    global_stats = summarize_slice(distances)
    str_slice = summarize_slice([(q, d) for q, d in distances if "str." in q.lower()])
    slash_slice = summarize_slice([(q, d) for q, d in distances if "/" in q])

    lines: list[str] = []
    lines.append(f"# Distance Evaluation: {args.label}")
    lines.append("")
    lines.append(f"- Input CSV: {args.input_csv}")
    lines.append(f"- Google cache: {args.google_cache}")
    lines.append(f"- Rows in CSV: {len(rows)}")
    lines.append(f"- Rows with comparable coordinates: {global_stats['count']}")
    lines.append("")
    lines.append("## Global")
    lines.append("")
    lines.append(f"- Median distance (m): {fmt(global_stats['median'])}")
    lines.append(f"- P90 distance (m): {fmt(global_stats['p90'])}")
    lines.append(
        f"- <= 50m: {global_stats['within_50']} ({pct(global_stats['within_50'], global_stats['count'])})"
    )
    lines.append(
        f"- <= 100m: {global_stats['within_100']} ({pct(global_stats['within_100'], global_stats['count'])})"
    )
    lines.append(
        f"- <= 250m: {global_stats['within_250']} ({pct(global_stats['within_250'], global_stats['count'])})"
    )

    lines.append("")
    lines.append("## Slice: street abbreviation (`str.`)")
    lines.append("")
    lines.append(f"- Comparable rows: {str_slice['count']}")
    lines.append(f"- Median distance (m): {fmt(str_slice['median'])}")
    lines.append(f"- P90 distance (m): {fmt(str_slice['p90'])}")
    lines.append(f"- <= 100m: {str_slice['within_100']} ({pct(str_slice['within_100'], str_slice['count'])})")

    lines.append("")
    lines.append("## Slice: slash housenumber (`/`)")
    lines.append("")
    lines.append(f"- Comparable rows: {slash_slice['count']}")
    lines.append(f"- Median distance (m): {fmt(slash_slice['median'])}")
    lines.append(f"- P90 distance (m): {fmt(slash_slice['p90'])}")
    lines.append(
        f"- <= 100m: {slash_slice['within_100']} ({pct(slash_slice['within_100'], slash_slice['count'])})"
    )

    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"label={args.label}")
    print(f"comparable_rows={global_stats['count']}")
    print(f"median_m={fmt(global_stats['median'])}")
    print(f"p90_m={fmt(global_stats['p90'])}")
    print(f"report={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
