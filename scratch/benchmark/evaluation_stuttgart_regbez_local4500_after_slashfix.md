# Distance Evaluation: stuttgart-regbez-local4500-after-slashfix

- Input CSV: /home/elias/goat/data/benchmark/geocoding_unique_stuttgart_regbez_internal_after_slashfix.csv
- Google cache: /home/elias/goat/data/benchmark/google_cache.jsonl
- Rows in CSV: 1319
- Rows with comparable coordinates: 1318

## Global

- Median distance (m): 6.42
- P90 distance (m): 39.28
- <= 50m: 1210 (91.81%)
- <= 100m: 1246 (94.54%)
- <= 250m: 1268 (96.21%)

## Slice: street abbreviation (`str.`)

- Comparable rows: 1033
- Median distance (m): 6.21
- P90 distance (m): 37.43
- <= 100m: 977 (94.58%)

## Slice: slash housenumber (`/`)

- Comparable rows: 46
- Median distance (m): 37.67
- P90 distance (m): 442.18
- <= 100m: 34 (73.91%)