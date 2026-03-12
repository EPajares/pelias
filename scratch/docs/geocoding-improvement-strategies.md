# Geocoder Improvement Strategies (Google as Gold Standard)

Date: 2026-03-01  
Scope: Compare internal geocoder against Google Geocoding API and improve weak spots.

## Goal

Use Google as reference truth (gold standard) and systematically reduce quality gaps in our geocoder.

## Benchmark Principle

For each input address:
1. Query Google (gold output).
2. Query internal geocoder.
3. Compare outputs with quantitative metrics and error categories.
4. Prioritize fixes by impact (frequency x severity).

## Evaluation Metrics

### 1) Match coverage
- % of queries with valid result
- % of queries with no result
- % of queries with fallback-only result

### 2) Positional accuracy against Google
- Median distance (meters)
- P90 distance (meters)
- % within 25m / 50m / 100m / 250m

### 3) Semantic agreement
- Same postcode rate
- Same city/locality rate
- Same street rate
- House number exact-match rate

### 4) Precision quality
- Distribution of internal match types (`exact`, `interpolated`, `fallback`, etc.)
- Agreement with Google location granularity (`ROOFTOP`, `RANGE_INTERPOLATED`, etc.)

## Test Dataset Strategy

Use two layers of test data:

1. **General benchmark set**
- Unique rows from [data/geocoding_unique.csv](data/geocoding_unique.csv)
- Broad quality baseline across all addresses

2. **Targeted failure sets**
- Curated subsets for known weak patterns
- Used for regression testing after each parser/index change

## Gold-Standard Comparison Workflow

1. Keep Google outputs fixed in cache (single source of truth snapshot).
2. Run internal geocoder repeatedly after each improvement.
3. Compare new internal run vs same Google snapshot.
4. Track delta metrics (before/after).

This isolates internal improvements without paying for repeated Google calls.

## Known Issue 1: `str.` vs `straße` / `strasse`

### Problem
Internal geocoder often fails when street abbreviations use `str.`.

### Hypothesis
Tokenizer/normalization pipeline does not robustly canonicalize German street variants before matching.

### Targeted benchmark slice
Build a dedicated subset with variants of same address:
- `Musterstr. 10, 12345 Stadt`
- `Musterstraße 10, 12345 Stadt`
- `Musterstrasse 10, 12345 Stadt`

### Success criteria
- High agreement across variants (same or near-identical coordinates)
- Significant reduction in variant-based failures
- Street-level semantic agreement close to Google for all variants

### Improvement strategies
- Add preprocessing rules for German street suffix normalization:
  - `str.` -> `straße`
  - `strasse` -> `straße` (or canonical internal token)
- Normalize Unicode and transliterations consistently (`ß` vs `ss`).
- Apply normalization both at index-time and query-time to avoid asymmetry.

## Known Issue 2: House numbers like `17/1`

### Problem
Internal geocoder struggles with fractional/slash house numbers (example: `17/1`).

### Hypothesis
House number parser is either rejecting slash format or not generating equivalent candidates.

### Targeted benchmark slice
Build a dedicated subset with house number variants:
- `17/1`
- `17-1`
- `17 1`
- `17a` (control for alphanumeric handling)

### Success criteria
- Increased match rate for slash-number inputs
- Reduced distance error vs Google on this subset
- Correct house-number semantic extraction where available

### Improvement strategies
- Extend house number tokenizer to support slash components.
- Generate candidate expansions for matching:
  - literal (`17/1`)
  - normalized (`17-1`, `17 1`)
- Ensure interpolation/address matching can consume slash-normalized forms.

## Error Taxonomy for Prioritization

Label each mismatch with one root cause category:
- Street normalization issue
- House number parsing issue
- Postcode mismatch
- Locality mismatch
- Ranking issue (correct candidate not top-1)
- No data/index coverage
- Fallback-only geocoding

Then prioritize by:
- Count of errors in category
- Average distance penalty in category

## Iterative Improvement Loop

For each release cycle:
1. Implement one parser/normalization improvement.
2. Re-run internal geocoder on unique dataset.
3. Recompute benchmark metrics vs fixed Google cache.
4. Re-run targeted issue subsets.
5. Ship only if targeted metrics improve and no major regressions appear.

## Suggested Output Artifacts

- Internal run output: [data/geocoding_unique_internal.csv](data/geocoding_unique_internal.csv)
- Google cache: [data/benchmark/google_cache.jsonl](data/benchmark/google_cache.jsonl)
- Comparison rows: [data/benchmark/comparison_results.csv](data/benchmark/comparison_results.csv)
- Summary metrics: [data/benchmark/summary_metrics.md](data/benchmark/summary_metrics.md)
- New targeted regression sets (recommended):
  - [data/benchmark/testset_street_abbrev.csv](data/benchmark/testset_street_abbrev.csv)
  - [data/benchmark/testset_housenumber_slash.csv](data/benchmark/testset_housenumber_slash.csv)

## Practical Next Steps

1. Extract top failing rows from current comparison output.
2. Create the two targeted testset CSVs.
3. Implement normalization/parser fixes for `str.` and `17/1`.
4. Re-run internal geocoder and compare against same Google cache.
5. Track before/after metrics in a changelog table.

## Current Baseline Snapshot (from existing run)

- Total compared rows: `7247`
- Median distance vs Google: `7.08m`
- P90 distance vs Google: `72.65m`
- Within `100m`: `91.29%`
- Tail issue remains large (`P95 ~ 388.98m`), driven by specific parsing/ranking failures.

Targeted slices generated:
- Street abbreviation slice: [data/benchmark/testset_street_abbrev.csv](data/benchmark/testset_street_abbrev.csv)
  - Rows: `5516`
  - Over `100m`: `497`
- Slash housenumber slice: [data/benchmark/testset_housenumber_slash.csv](data/benchmark/testset_housenumber_slash.csv)
  - Rows: `258`
  - Over `100m`: `110`

## Prioritized Improvement Backlog

### Priority 1 — Canonical street normalization (`str.` / `straße` / `strasse`)

Why first:
- High frequency in dataset and substantial share of large errors.

Implementation suggestions:
- Query preprocessing dictionary for German street suffixes:
  - `str.` -> `straße`
  - `strasse` -> `straße`
- Keep a parallel normalized token form to avoid losing original text.
- Ensure same normalization logic is applied during index-time and query-time.

Acceptance target:
- On `testset_street_abbrev.csv`, reduce `>100m` rows by at least `25%` in first iteration.

### Priority 2 — Slash house-number parser support (`17/1`)

Why second:
- Small subset but very high failure ratio (currently severe).

Implementation suggestions:
- Extend house-number tokenizer to treat slash as structured suffix instead of noise.
- Candidate expansion for matching/interpolation:
  - `17/1`, `17-1`, `17 1`, and base number fallback `17`.
- Promote exact slash-format matches above fallback locality results.

Acceptance target:
- On `testset_housenumber_slash.csv`, reduce `>100m` rows by at least `40%` in first iteration.

### Priority 3 — Fallback suppression when strong structured fields exist

Observation:
- Many large outliers come from fallback results despite having street+postcode+city.

Implementation suggestions:
- Add a ranking penalty for locality/neighbourhood fallback when structured address fields are parsed.
- Require minimum street similarity threshold before returning fallback as top-1.

Acceptance target:
- Reduce extreme outliers (`>1km`) by at least `30%` overall.

### Priority 4 — Top-1 ranking calibration

Implementation suggestions:
- Increase weight for postcode and city exact agreement.
- Add tie-breaker favoring exact house-number tokens over broad street/area matches.

Acceptance target:
- Improve `<=50m` and `<=100m` rates without reducing overall coverage.

## Suggested Iteration Cadence

For each change-set:
1. Run internal geocoder on unique set (`data/geocoding_unique.csv`).
2. Compare against fixed Google cache (no new Google calls).
3. Recompute whole-dataset metrics + two targeted-slice metrics.
4. Keep change only if tail metrics improve and no major regressions occur.
