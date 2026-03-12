# Distance Evaluation: stuttgart-regbez-local4500

- Input CSV: /home/elias/goat/data/benchmark/geocoding_unique_stuttgart_regbez_internal.csv
- Google cache: /home/elias/goat/data/benchmark/google_cache.jsonl
- Rows in CSV: 1319
- Rows with comparable coordinates: 1318

## Global

- Median distance (m): 6.42
- P90 distance (m): 39.59
- <= 50m: 1207 (91.58%)
- <= 100m: 1244 (94.39%)
- <= 250m: 1268 (96.21%)

## Slice: street abbreviation (`str.`)

- Comparable rows: 1033
- Median distance (m): 6.21
- P90 distance (m): 38.86
- <= 100m: 976 (94.48%)

## Slice: slash housenumber (`/`)

- Comparable rows: 46
- Median distance (m): 63.98
- P90 distance (m): 442.18
- <= 100m: 32 (69.57%)