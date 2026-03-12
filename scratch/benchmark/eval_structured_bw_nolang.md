# Distance Evaluation: structured_bw_nolang

- Input CSV: /home/elias/goat/data/geocoding_unique_internal_structured_bw_nolang.csv
- Google cache: /home/elias/goat/data/benchmark/google_cache.jsonl
- Rows in CSV: 3849
- Rows with comparable coordinates: 3849

## Global

- Median distance (m): 6.01
- P90 distance (m): 51.13
- <= 50m: 3458 (89.84%)
- <= 100m: 3581 (93.04%)
- <= 250m: 3674 (95.45%)

## Slice: street abbreviation (`str.`)

- Comparable rows: 2924
- Median distance (m): 5.91
- P90 distance (m): 48.11
- <= 100m: 2724 (93.16%)

## Slice: slash housenumber (`/`)

- Comparable rows: 135
- Median distance (m): 13.55
- P90 distance (m): 182.33
- <= 100m: 110 (81.48%)