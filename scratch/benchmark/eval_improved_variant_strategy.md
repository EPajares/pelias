# Distance Evaluation: improved_variant_strategy

- Input CSV: /home/elias/goat/data/geocoding_unique_internal_improved.csv
- Google cache: /home/elias/goat/data/benchmark/google_cache.jsonl
- Rows in CSV: 3849
- Rows with comparable coordinates: 3849

## Global

- Median distance (m): 6.42
- P90 distance (m): 47.93
- <= 50m: 3476 (90.31%)
- <= 100m: 3587 (93.19%)
- <= 250m: 3660 (95.09%)

## Slice: street abbreviation (`str.`)

- Comparable rows: 2924
- Median distance (m): 6.37
- P90 distance (m): 43.07
- <= 100m: 2733 (93.47%)

## Slice: slash housenumber (`/`)

- Comparable rows: 135
- Median distance (m): 10.35
- P90 distance (m): 81.36
- <= 100m: 123 (91.11%)