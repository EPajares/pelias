#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Geocode a unique-address CSV using internal geocoding service settings from .env"
    )
    parser.add_argument("--input-csv", default="data/geocoding_unique.csv")
    parser.add_argument("--output-csv", default="data/geocoding_unique_internal.csv")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0, help="Optional row limit for testing. 0 means all rows.")
    return parser.parse_args()


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def call_internal_geocoder(base_url: str, auth_header: str | None, query_text: str, timeout_seconds: int) -> dict[str, Any]:
    params = urlencode({"text": query_text, "lang": "de", "size": 1})
    url = f"{base_url.rstrip('/')}/v1/search?{params}"
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    req = Request(url, headers=headers, method="GET")

    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "REQUEST_ERROR",
            "lat": None,
            "lon": None,
            "confidence": None,
            "match_type": None,
            "accuracy": None,
            "label": None,
            "layer": None,
            "source": None,
            "error": str(exc),
        }

    features = payload.get("features") or []
    if not features:
        return {
            "status": "NO_RESULTS",
            "lat": None,
            "lon": None,
            "confidence": None,
            "match_type": None,
            "accuracy": None,
            "label": None,
            "layer": None,
            "source": None,
            "error": None,
        }

    first = features[0]
    coords = ((first.get("geometry") or {}).get("coordinates") or [None, None])
    props = first.get("properties") or {}

    return {
        "status": "OK",
        "lat": coords[1] if len(coords) > 1 else None,
        "lon": coords[0] if len(coords) > 0 else None,
        "confidence": props.get("confidence"),
        "match_type": props.get("match_type"),
        "accuracy": props.get("accuracy"),
        "label": props.get("label"),
        "layer": props.get("layer"),
        "source": props.get("source"),
        "error": None,
    }


def main() -> int:
    args = parse_args()

    env = load_env(Path(args.env_file))
    geocoding_url = env.get("GEOCODING_URL")
    geocoding_auth = env.get("GEOCODING_AUTHORIZATION")

    if not geocoding_url:
        raise SystemExit("Missing GEOCODING_URL in env file")

    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8", newline="") as f_in:
        reader = csv.DictReader(f_in)
        if not reader.fieldnames:
            raise SystemExit("Input CSV has no headers")

        output_fields = list(reader.fieldnames) + [
            "internal_service_status",
            "internal_service_latitude",
            "internal_service_longitude",
            "internal_service_confidence",
            "internal_service_match_type",
            "internal_service_accuracy",
            "internal_service_label",
            "internal_service_layer",
            "internal_service_source",
            "internal_service_error",
        ]

        with output_path.open("w", encoding="utf-8", newline="") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=output_fields)
            writer.writeheader()

            processed = 0
            ok_count = 0
            no_results = 0
            error_count = 0

            for row in reader:
                query_text = (row.get("geocode_input_text") or "").strip()
                result = call_internal_geocoder(geocoding_url, geocoding_auth, query_text, args.timeout_seconds)

                status = result["status"]
                if status == "OK":
                    ok_count += 1
                elif status == "NO_RESULTS":
                    no_results += 1
                else:
                    error_count += 1

                row_out = dict(row)
                row_out.update(
                    {
                        "internal_service_status": status,
                        "internal_service_latitude": result["lat"],
                        "internal_service_longitude": result["lon"],
                        "internal_service_confidence": result["confidence"],
                        "internal_service_match_type": result["match_type"],
                        "internal_service_accuracy": result["accuracy"],
                        "internal_service_label": result["label"],
                        "internal_service_layer": result["layer"],
                        "internal_service_source": result["source"],
                        "internal_service_error": result["error"],
                    }
                )
                writer.writerow(row_out)

                processed += 1
                if processed % 250 == 0:
                    print(f"progress={processed}")

                if args.limit > 0 and processed >= args.limit:
                    break

                if args.sleep_seconds > 0:
                    time.sleep(args.sleep_seconds)

    print(f"processed={processed}")
    print(f"ok={ok_count}")
    print(f"no_results={no_results}")
    print(f"errors={error_count}")
    print(f"output_file={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
