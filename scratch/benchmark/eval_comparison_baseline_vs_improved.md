# Baseline vs Improved (Distance Benchmark)

- Baseline report: data/benchmark/eval_baseline_current.md
- Improved report: data/benchmark/eval_improved_variant_strategy.md

## Global Metrics

| Metric | Baseline | Improved | Delta |
|---|---:|---:|---:|
| Median distance (m) | 6.49 | 6.42 | -0.07 |
| P90 distance (m) | 61.44 | 47.93 | -13.51 |
| <= 50m | 89.04% | 90.31% | +1.27 pp |
| <= 100m | 92.15% | 93.19% | +1.04 pp |
| <= 250m | 94.39% | 95.09% | +0.70 pp |

## Targeted Slice Metrics

| Slice Metric | Baseline | Improved | Delta |
|---|---:|---:|---:|
| str. median (m) | 6.46 | 6.37 | -0.09 |
| str. p90 (m) | 60.80 | 43.07 | -17.73 |
| str. <=100m | 92.10% | 93.47% | +1.37 pp |
| slash median (m) | 61.09 | 10.35 | -50.74 |
| slash p90 (m) | 528.93 | 81.36 | -447.57 |
| slash <=100m | 62.22% | 91.11% | +28.89 pp |