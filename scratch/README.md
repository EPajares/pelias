# Pelias Scratch — Testing, Benchmarking & Bug Fixes

Working area for Pelias geocoder testing, benchmarking against Google, and developing fixes for German address parsing issues.

Migrated from `goat` repo (`tools/pelias-germany-no-oa/` and `data/benchmark/`) on 2026-03-12.

## Directory Layout

```
scratch/
├── benchmark/                          # Geocoding benchmark data & scripts
│   ├── geocoding.csv                   # Full BW doctor addresses (7,247 rows)
│   ├── geocoding_unique.csv            # Deduplicated addresses (3,849 rows)
│   ├── google_cache.jsonl              # Google Geocoding API results (gold standard)
│   ├── testset_street_abbrev.csv       # Regression: str./straße/strasse variants
│   ├── testset_housenumber_slash.csv   # Regression: 17/1 slash house numbers
│   ├── run_geocoding_benchmark.py      # Run Google vs internal benchmark
│   ├── run_internal_geocode_unique.py  # Query internal geocoder
│   └── evaluate_internal_vs_google.py  # Compare & produce metrics
├── docs/                               # Research & strategy documents
│   ├── geocoding-benchmark-strategy.md
│   └── geocoding-improvement-strategies.md
├── patches/                            # Pelias API bug-fix patches (reference)
│   ├── Interpolation.js                # Fix: array street + slash house numbers
│   ├── pelias-sorting-index.js         # Fix: ranking postcode/city mismatch
│   └── Dockerfile                      # Patch overlay for pelias/api:master
├── projects/                           # pelias-docker project configurations
│   ├── germany-no-oa/                  # Full Germany, no OpenAddresses
│   └── stuttgart-regbez/               # Stuttgart region (fast iteration)
└── scripts/                            # Build & run helpers
    ├── run-build-no-oa.sh
    └── germany-no-oa-README.md
```

## Repos to Fork

Only **2** upstream repos need forking for the current bug fixes:

| Repo | Fix | File |
|------|-----|------|
| [pelias/api](https://github.com/pelias/api) | Array street params + slash house numbers | `service/configurations/Interpolation.js` |
| [pelias/sorting](https://github.com/pelias/sorting) | Ranking postcode/city mismatch penalty | `index.js` |

`pelias-sorting` is an npm dep of `pelias/api` — point `package.json` at your fork to bundle both.

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
