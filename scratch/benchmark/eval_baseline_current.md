# Distance Evaluation: baseline_current

- Input CSV: /home/elias/goat/data/geocoding_unique.csv
- Google cache: /home/elias/goat/data/benchmark/google_cache.jsonl
- Rows in CSV: 3849
- Rows with comparable coordinates: 3849

## Global

- Median distance (m): 6.49
- P90 distance (m): 61.44
- <= 50m: 3427 (89.04%)
- <= 100m: 3547 (92.15%)
- <= 250m: 3633 (94.39%)

## Slice: street abbreviation (`str.`)

- Comparable rows: 2924
- Median distance (m): 6.46
- P90 distance (m): 60.80
- <= 100m: 2693 (92.10%)

## Slice: slash housenumber (`/`)

- Comparable rows: 135
- Median distance (m): 61.09
- P90 distance (m): 528.93
- <= 100m: 84 (62.22%)