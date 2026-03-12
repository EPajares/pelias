# Pelias Scratch — Testing, Benchmarking & Bug Fixes

Working area for Pelias geocoder testing, benchmarking against Google, and developing fixes for German address parsing issues.

Migrated from `goat` repo (`tools/pelias-germany-no-oa/` and `data/benchmark/`) on 2026-03-12.

## Directory Layout

```
scratch/
├── benchmark/          # Geocoding benchmark data, scripts, results
│   ├── geocoding*.csv          # Test address datasets (BW doctor addresses)
│   ├── google_cache.jsonl      # Cached Google Geocoding API responses
│   ├── comparison_results.csv  # Internal vs Google comparison
│   ├── run_*.py                # Benchmark & evaluation scripts
│   ├── eval_*.md               # Evaluation result summaries
│   ├── testset_*.csv           # Targeted regression test sets
│   └── *.geojson               # Error visualisation layers
├── docs/               # Research & strategy documents
│   ├── geocoding-benchmark-strategy.md
│   └── geocoding-improvement-strategies.md
├── patches/            # Pelias API bug-fix patches (JS files + Dockerfile)
│   ├── Interpolation.js        # Fix: array street params & slash house numbers
│   ├── pelias-sorting-index.js # Fix: postcode/city mismatch penalty in ranking
│   └── Dockerfile              # Patch overlay for pelias/api:master
├── projects/           # Pelias-docker project configurations
│   ├── germany-no-oa/         # Full Germany, no OpenAddresses
│   └── stuttgart-regbez/      # Stuttgart region (smaller, for fast iteration)
└── scripts/            # Build & run scripts
    ├── run-build-no-oa.sh
    └── germany-no-oa-README.md
```

## Known Bugs (found & patched)

1. **Array street params → 400 error** — When libpostal returns multiple street name variants, the interpolation service receives `street` as an array and returns HTTP 400 "invalid street". Fix in `Interpolation.js`: pick first valid string from array.

2. **Slash house numbers (`17/1`)** — libpostal parses `17/1` as unit=17 + housenumber=1 (inverted). Fix in `Interpolation.js`: detect slash pattern in original query text and swap to use the correct number.

3. **Ranking: postcode/city mismatch** — Addresses from wrong city/postcode ranked above correct matches due to raw ES score. Fix in `pelias-sorting-index.js`: apply penalty when result postcode or locality doesn't match query.

## Baseline Metrics (from benchmark)

- **Dataset**: 7,247 BW doctor addresses → 3,430 unique queries
- **Median distance vs Google**: 7.08 m
- **P90**: 72.65 m
- **Within 100 m**: 91.29%
- **P95**: 388.98 m (tail driven by `str.` abbreviation and slash house number issues)
