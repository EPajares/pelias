# Wrong Cases GeoJSON (with explicit point roles)

- `point_role=internal`: your Stuttgart geocoded point
- `point_role=google`: Google baseline point
- `feature_kind=error_vector`: line from internal -> google (`line_from=internal`, `line_to=google`)

- Internal points: 72
- Google points: 73
- Error vectors: 72
- GeoJSON: /home/elias/goat/data/benchmark/wrong_cases_stuttgart_regbez_after_slashfix_with_points.geojson