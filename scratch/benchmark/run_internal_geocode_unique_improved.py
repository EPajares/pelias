#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Geocode unique addresses with query normalization + variant retry strategy"
    )
    parser.add_argument("--input-csv", default="data/geocoding_unique.csv")
    parser.add_argument("--output-csv", default="data/geocoding_unique_internal_improved.csv")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-features", type=int, default=5)
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


def canonicalize_query(text: str) -> str:
    q = text.strip()
    q = re.sub(r"(?i)\bstr\.", "straße", q)
    q = re.sub(r"(?i)strasse", "straße", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def variant_queries(query_text: str) -> list[str]:
    seeds: set[str] = {query_text.strip()}
    canonical = canonicalize_query(query_text)
    seeds.add(canonical)

    expanded: set[str] = set(seeds)
    for q in list(seeds):
        # slash number variants (17/1 -> 17-1, 17 1)
        m = re.search(r"(\d+)\s*/\s*([0-9]+[a-zA-Z]?)", q)
        if m:
            a, b = m.group(1), m.group(2)
            expanded.add(re.sub(r"(\d+)\s*/\s*([0-9]+[a-zA-Z]?)", f"{a}-{b}", q, count=1))
            expanded.add(re.sub(r"(\d+)\s*/\s*([0-9]+[a-zA-Z]?)", f"{a} {b}", q, count=1))
            expanded.add(re.sub(r"(\d+)\s*/\s*([0-9]+[a-zA-Z]?)", f"{a}", q, count=1))

        # ß / ss variants
        if "ß" in q:
            expanded.add(q.replace("ß", "ss"))
        if "ss" in q:
            expanded.add(q.replace("ss", "ß"))

    # stable order: shortest first can help with broader candidate retrieval
    variants = sorted({v.strip() for v in expanded if v.strip()}, key=lambda s: (len(s), s))
    # ensure original query is tested first
    if query_text.strip() in variants:
        variants.remove(query_text.strip())
    return [query_text.strip(), *variants]


def call_search(base_url: str, auth_header: str | None, query_text: str, timeout_seconds: int, size: int) -> dict[str, Any]:
    params = urlencode({"text": query_text, "lang": "de", "size": size})
    url = f"{base_url.rstrip('/')}/v1/search?{params}"
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=timeout_seconds) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_text(v: str | None) -> str:
    if not v:
        return ""
    text = v.lower().strip()
    text = text.replace("str.", "straße")
    text = text.replace("strasse", "straße")
    text = re.sub(r"\s+", " ", text)
    return text


def extract_house_number(query_text: str) -> str:
    m = re.search(r"\b(\d+\s*/\s*[0-9]+[a-zA-Z]?|\d+[a-zA-Z]?(-[0-9]+[a-zA-Z]?)?)\b", query_text)
    return (m.group(1).replace(" ", "") if m else "")


def score_feature(feature: dict[str, Any], row: dict[str, str], variant: str) -> float:
    props = feature.get("properties") or {}
    layer = (props.get("layer") or "").lower()
    match_type = (props.get("match_type") or "").lower()
    accuracy = (props.get("accuracy") or "").lower()
    confidence = float(props.get("confidence") or 0.0)

    score = 0.0

    if layer == "address":
        score += 140
    elif layer == "street":
        score += 90
    elif layer in {"locality", "neighbourhood"}:
        score -= 40

    if match_type == "exact":
        score += 45
    elif match_type == "fallback":
        score -= 35

    if accuracy == "point":
        score += 20
    elif accuracy == "centroid":
        score -= 15

    score += confidence * 20

    postal_expected = normalize_text(row.get("LO_PLZ"))
    postal_got = normalize_text(props.get("postalcode"))
    if postal_expected and postal_got and postal_expected == postal_got:
        score += 55

    city_expected = normalize_text(row.get("LO_ORT"))
    city_got = normalize_text(props.get("locality") or props.get("localadmin") or props.get("county"))
    if city_expected and city_got and city_expected in city_got:
        score += 40

    street_expected = normalize_text(row.get("LO_STRASSE"))
    street_expected = re.sub(r"\b\d+.*$", "", street_expected).strip()
    street_got = normalize_text(props.get("street") or props.get("name"))
    if street_expected and street_got:
        if street_expected in street_got or street_got in street_expected:
            score += 45

    house_expected = extract_house_number(row.get("geocode_input_text") or "")
    house_got = normalize_text(props.get("housenumber")).replace(" ", "")
    if house_expected and house_got:
        if house_expected == house_got:
            score += 65
        elif house_expected.replace("/", "-") == house_got or house_expected.replace("/", "") == house_got:
            score += 35

    # small preference when variant itself is canonicalized and shorter
    if normalize_text(variant) == canonicalize_query(variant).lower():
        score += 2

    return score


def pick_best(base_url: str, auth_header: str | None, row: dict[str, str], timeout_seconds: int, max_features: int) -> dict[str, Any]:
    query = (row.get("geocode_input_text") or "").strip()
    variants = variant_queries(query)

    best: dict[str, Any] | None = None
    best_score = -10**9
    last_error: str | None = None

    for variant in variants:
        try:
            payload = call_search(base_url, auth_header, variant, timeout_seconds, size=max_features)
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue

        for feature in payload.get("features") or []:
            score = score_feature(feature, row, variant)
            if score > best_score:
                best_score = score
                best = {
                    "variant": variant,
                    "score": score,
                    "feature": feature,
                }

    if best is None:
        return {
            "status": "NO_RESULTS" if last_error is None else "REQUEST_ERROR",
            "variant": None,
            "score": None,
            "lat": None,
            "lon": None,
            "confidence": None,
            "match_type": None,
            "accuracy": None,
            "label": None,
            "layer": None,
            "source": None,
            "error": last_error,
        }

    feature = best["feature"]
    props = feature.get("properties") or {}
    coords = ((feature.get("geometry") or {}).get("coordinates") or [None, None])
    return {
        "status": "OK",
        "variant": best["variant"],
        "score": best["score"],
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

    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with in_path.open("r", encoding="utf-8", newline="") as f_in:
        reader = csv.DictReader(f_in)
        if not reader.fieldnames:
            raise SystemExit("Input CSV has no headers")

        fields = list(reader.fieldnames) + [
            "improved_status",
            "improved_query_variant",
            "improved_score",
            "improved_latitude",
            "improved_longitude",
            "improved_confidence",
            "improved_match_type",
            "improved_accuracy",
            "improved_label",
            "improved_layer",
            "improved_source",
            "improved_error",
        ]

        processed = 0
        ok = 0
        no_results = 0
        errors = 0

        with out_path.open("w", encoding="utf-8", newline="") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fields)
            writer.writeheader()

            for row in reader:
                result = pick_best(geocoding_url, geocoding_auth, row, args.timeout_seconds, args.max_features)
                status = result["status"]
                if status == "OK":
                    ok += 1
                elif status == "NO_RESULTS":
                    no_results += 1
                else:
                    errors += 1

                out = dict(row)
                out.update(
                    {
                        "improved_status": status,
                        "improved_query_variant": result["variant"],
                        "improved_score": result["score"],
                        "improved_latitude": result["lat"],
                        "improved_longitude": result["lon"],
                        "improved_confidence": result["confidence"],
                        "improved_match_type": result["match_type"],
                        "improved_accuracy": result["accuracy"],
                        "improved_label": result["label"],
                        "improved_layer": result["layer"],
                        "improved_source": result["source"],
                        "improved_error": result["error"],
                    }
                )
                writer.writerow(out)

                processed += 1
                if processed % 200 == 0:
                    print(f"progress={processed}")

                if args.limit > 0 and processed >= args.limit:
                    break

                if args.sleep_seconds > 0:
                    time.sleep(args.sleep_seconds)

    print(f"processed={processed}")
    print(f"ok={ok}")
    print(f"no_results={no_results}")
    print(f"errors={errors}")
    print(f"output_file={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
