# Geocoding Benchmark Strategy (Internal Service vs Google Maps)

Date: 2026-03-01  
Dataset: `data/geocoding.csv` (7,249 rows)

## Objective

Benchmark geocoding quality of our service against Google Maps Geocoding API while controlling API cost.

## Scope and Cost Guardrails

- Start with **exactly 1 address** (pilot) before the full run.
- Then run Google geocoding **once for the full dataset**.
- In the full run, process addresses **one by one** with:
  - request throttling,
  - local result caching,
  - resume support.
- Use `geocode_input_text` as the canonical query string for both services.
- Deduplicate by `geocode_input_text` to avoid paying for duplicate requests.
- Never commit API keys to git-tracked files.

## Data Source

Input file: `data/geocoding.csv`

Relevant columns already present:
- `fid`
- `geocode_input_text`
- `geocode_latitude`
- `geocode_longitude`
- `geocode_confidence`
- `geocode_match_type`

These existing `geocode_*` columns can be treated as the current internal-service baseline output.

## Phase 1 — Single-Address Pilot (Low Cost)

### Pilot candidate

Use first row (`fid=1`):
- `Herrenstr. 29, Kißlegg, 88353`

### What to call

1. Our geocoding service for the pilot query.
2. Google Geocoding API for the same query.

### What to record

For each provider store at minimum:
- `query_text`
- `provider`
- `lat`
- `lon`
- `formatted_address`
- `place_id` (if available)
- `confidence` / `location_type` / `match_type` equivalents
- `raw_status` (OK, ZERO_RESULTS, etc.)
- `request_timestamp`

### Pilot pass criteria

- Both providers return a result.
- Distance between result points is within acceptable tolerance (e.g., <= 100m).
- Output schema is stable and can be reused for batch evaluation.

If pilot fails, stop and fix parsing/normalization before batch mode.

## Phase 2 — One-Time Full Google Run

After pilot approval:

1. Build a unique query set from `geocode_input_text`.
2. Query Google once per unique query and cache responses locally.
3. Reuse cached Google result for all rows with the same `geocode_input_text`.
4. Keep request throttling (e.g., 1 request/sec) and resume mode enabled.
5. Compare Google outputs to existing internal outputs in the CSV (`geocode_latitude`, `geocode_longitude`, `geocode_confidence`, `geocode_match_type`).

Estimated request volume for current file:
- Total rows: `7247`
- Unique `geocode_input_text`: `3430`

So the Google call count should be approximately `3430` (not `7247`) when deduplication is applied.

## Normalization Strategy

Map both providers to a common output shape:

- `fid`
- `query_text`
- `provider`
- `lat`
- `lon`
- `normalized_confidence`
- `normalized_match_type`
- `normalized_precision` (rooftop/range/interpolated/centroid)
- `formatted_address`
- `country_code`
- `postal_code`
- `locality`
- `error`

Notes:
- Google `geometry.location_type` can be mapped to precision categories.
- Internal service fields should be mapped to same categories where possible.

## Quality Metrics

Primary metrics:
- **Coverage**: `% rows with valid result`
- **Agreement**: `% rows where distance(internal, google) <= threshold`
- **Median distance error** between providers
- **P90 distance error**

Secondary metrics:
- Match-type distribution (`exact`, `interpolated`, `fallback`, etc.)
- Country/postcode consistency rates
- Error-rate by provider

Distance formula:
- Use haversine distance in meters between coordinates.

## Cost-Control Requirements

- API key loaded from environment variable only (example: `GOOGLE_MAPS_API_KEY`).
- Do not print full key in logs.
- Do not write key to benchmark output files.
- Cache all Google responses by a deterministic key (`query_text` hash).
- Support resume mode to continue interrupted runs without re-requesting processed rows.

## Suggested Output Files

Under `data/benchmark/`:

- `pilot_results.json`
- `google_cache.jsonl`
- `internal_cache.jsonl`
- `comparison_results.csv`
- `summary_metrics.md`

## Minimal Execution Plan

1. Implement pilot script for one `fid` (default: 1).
2. Validate normalization and metric calculation on pilot.
3. Run full Google pass once over unique query set with caching/resume.
4. Expand cached Google results back to all rows by `geocode_input_text`.
5. Compute and review summary metrics.

## Open Decisions

- Final threshold for “agreement” distance (50m, 100m, 250m?).
- Whether to treat Google as reference truth or only as comparison baseline.
- How to score ties when both providers return plausible but different points.

## Security Note

A Google API key was provided for testing. Rotate it if it has been exposed in shared channels, and restrict it by:
- IP allowlist (if possible)
- API scope (Geocoding only)
- daily quota/budget caps
