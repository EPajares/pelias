#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PELIAS_DIR="${ROOT_DIR}/pelias-docker"
PROJECT_DIR="${PELIAS_DIR}/projects/germany-no-oa"
PELIAS="${PELIAS_DIR}/pelias"
GERMANY_POLYLINES_URL="https://data.geocode.earth/osm/2022-35/germany-valhalla.polylines.0sv.gz"
MIN_POLYLINE_BYTES=1000000

cd "${PROJECT_DIR}"
mkdir -p data

"${PELIAS}" compose pull
"${PELIAS}" elastic start
"${PELIAS}" elastic wait
curl -s -X DELETE "http://localhost:9200/pelias" >/dev/null || true
"${PELIAS}" elastic create

if [[ ! -f "data/openstreetmap/germany-latest.osm.pbf" ]]; then
	"${PELIAS}" download osm
else
	echo "Using existing OSM extract: data/openstreetmap/germany-latest.osm.pbf"
fi

if [[ ! -f "data/whosonfirst/sqlite/whosonfirst-data-admin-de-latest.db" ]]; then
	"${PELIAS}" download wof
else
	echo "Using existing WOF sqlite: data/whosonfirst/sqlite/whosonfirst-data-admin-de-latest.db"
fi

mkdir -p data/polylines
POLYLINE_BYTES=0
if [[ -f "data/polylines/extract.0sv" ]]; then
	POLYLINE_BYTES=$(wc -c < data/polylines/extract.0sv || echo 0)
fi

if [[ "${POLYLINE_BYTES}" -lt "${MIN_POLYLINE_BYTES}" ]]; then
	rm -f data/polylines/extract.0sv data/polylines/extract.0sv.gz
	echo "Downloading prebuilt Germany valhalla polylines..."
	if curl -fsSL "${GERMANY_POLYLINES_URL}" -o data/polylines/extract.0sv.gz; then
		gunzip -f data/polylines/extract.0sv.gz
	else
		echo "Prebuilt polylines download failed, trying local polyline extraction from OSM..."
		"${PELIAS}" prepare polylines
	fi
else
	echo "Using existing polylines file: data/polylines/extract.0sv (${POLYLINE_BYTES} bytes)"
fi

"${PELIAS}" prepare placeholder
"${PELIAS}" prepare interpolation

"${PELIAS}" import openstreetmap
"${PELIAS}" import whosonfirst
"${PELIAS}" import placeholder
"${PELIAS}" import interpolation

"${PELIAS}" compose up
