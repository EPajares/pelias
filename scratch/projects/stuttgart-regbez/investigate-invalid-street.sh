#!/usr/bin/env bash

set -euo pipefail

API_URL="${API_URL:-http://localhost:4500/v1/search}"
INTERP_URL="${INTERP_URL:-http://localhost:5430/search/geojson}"

echo "[1] Find anchor coordinate from API"
read lat lon <<<"$(curl -sS -G "$API_URL" \
  --data-urlencode 'text=Königstraße 90' \
  --data-urlencode 'size=1' \
  | jq -r '.features[0].geometry.coordinates | "\(.[1]) \(.[0])"')"
echo "anchor lat/lon: $lat,$lon"

echo
echo "[2] Working interpolation call (single street parameter)"
curl -sS -i -G "$INTERP_URL" \
  --data-urlencode 'number=101' \
  --data-urlencode 'street=Königstraße' \
  --data-urlencode "lat=$lat" \
  --data-urlencode "lon=$lon" \
  | sed -n '1,20p'

echo
echo "[3] Failing interpolation call (multiple street parameters)"
curl -sS -i -G "$INTERP_URL" \
  --data-urlencode 'number=101' \
  --data-urlencode 'street=B14-Brücke Fahrtrichtung Stuttgart' \
  --data-urlencode 'street=B14- Brücke Fahrtrichtung Stuttgart' \
  --data-urlencode 'lat=48.954128' \
  --data-urlencode 'lon=9.415766' \
  | sed -n '1,20p'

echo
echo "[4] Control call with comma-joined street alias list"
curl -sS -i -G "$INTERP_URL" \
  --data-urlencode 'number=101' \
  --data-urlencode 'street=B14-Brücke Fahrtrichtung Stuttgart,B14- Brücke Fahrtrichtung Stuttgart' \
  --data-urlencode 'lat=48.954128' \
  --data-urlencode 'lon=9.415766' \
  | sed -n '1,20p'

echo
echo "Done. Expected pattern:"
echo "- single street => 200 (possibly Feature or {})"
echo "- repeated street params => 400 {\"message\":\"invalid street\"}"
echo "- comma-joined aliases => 200 {}"
