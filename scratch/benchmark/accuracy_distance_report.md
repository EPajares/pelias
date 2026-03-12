# Accuracy Test (Distance-Based)

Using existing internal geocoding results (no request changes), compared to Google baseline.

## Dataset

- Source: data/benchmark/comparison_results.csv
- Total rows: 7247
- Rows with distance available: 7247

## Distance Metrics (meters)

- Mean: 1358.27
- Median: 7.08
- P90: 72.65
- P95: 388.98

## Threshold Accuracy

- <= 25m: 5896 (81.36%)
- <= 50m: 6401 (88.33%)
- <= 100m: 6616 (91.29%)
- <= 250m: 6795 (93.76%)
- <= 500m: 6944 (95.82%)

## Google Status Counts

- OK: 7247

## Top 20 Largest Distance Deltas

| fid | query_text | internal_match_type | distance_m |
|---:|---|---|---:|
| 5684 | Reinhardtstr. 17/1, Ellwangen (Jagst), 73479 | fallback | 452678.560 |
| 5685 | Reinhardtstr. 17/1, Ellwangen (Jagst), 73479 | fallback | 452678.560 |
| 5686 | Reinhardtstr. 17/1, Ellwangen (Jagst), 73479 | fallback | 452678.560 |
| 5687 | Reinhardtstr. 17/1, Ellwangen (Jagst), 73479 | fallback | 452678.560 |
| 5688 | Reinhardtstr. 17/1, Ellwangen (Jagst), 73479 | fallback | 452678.560 |
| 2115 | Falkauerstr. 1, Feldberg (Schwarzwald), 79868 | fallback | 377958.976 |
| 6890 | J7, 18-19, Mannheim, 68159 | exact | 338545.880 |
| 6891 | J7, 18-19, Mannheim, 68159 | exact | 338545.880 |
| 4487 | Hauptstr. 67-69, Mühlhausen, 69242 | fallback | 258117.220 |
| 7074 | Mörikestr. 17, Bingen, 72511 | exact | 227121.988 |
| 7075 | Mörikestr. 17, Bingen, 72511 | exact | 227121.988 |
| 7076 | Mörikestr. 17, Bingen, 72511 | exact | 227121.988 |
| 4737 | Bahnhofstr. 1-3, Walldorf, 69190 | fallback | 192397.646 |
| 3604 | Flughafen Terminal 1 West, Leinfelden-Echterdingen, 70771 | exact | 157046.974 |
| 959 | Karlstr. 15, Rheinfelden (Baden), 79618 | exact | 138556.510 |
| 1037 | Zähringerstr. 21, Rheinfelden (Baden), 79618 | fallback | 138443.323 |
| 1038 | Zähringerstr. 21, Rheinfelden (Baden), 79618 | fallback | 138443.323 |
| 1039 | Zähringerstr. 21, Rheinfelden (Baden), 79618 | fallback | 138443.323 |
| 1409 | Kapuzinerstr. 2, Rheinfelden (Baden), 79618 | fallback | 138193.169 |
| 1359 | Kapuzinerstr. 4, Rheinfelden (Baden), 79618 | exact | 138185.217 |