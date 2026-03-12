# Distance Evaluation: structured_query

- Input CSV: /home/elias/goat/data/geocoding_unique_internal_structured.csv
- Google cache: /home/elias/goat/data/benchmark/google_cache.jsonl
- Rows in CSV: 3849
- Rows with comparable coordinates: 3849

## Global

- Median distance (m): 6.37
- P90 distance (m): 46.16
- <= 50m: 3486 (90.57%)
- <= 100m: 3591 (93.30%)
- <= 250m: 3669 (95.32%)

## Slice: street abbreviation (`str.`)

- Comparable rows: 2924
- Median distance (m): 6.28
- P90 distance (m): 40.96
- <= 100m: 2734 (93.50%)

## Slice: slash housenumber (`/`)

- Comparable rows: 135
- Median distance (m): 11.61
- P90 distance (m): 157.75
- <= 100m: 112 (82.96%)