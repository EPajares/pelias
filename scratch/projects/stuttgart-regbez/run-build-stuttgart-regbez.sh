#!/usr/bin/env bash

set -euo pipefail

# Run from within this project directory:
#   cd tools/pelias-germany-no-oa/pelias-docker/projects/stuttgart-regbez
#   ./run-build-stuttgart-regbez.sh

echo "[1/12] Pulling docker images"
../../pelias compose pull

echo "[2/12] Starting elasticsearch"
../../pelias compose up elasticsearch

echo "[3/12] Waiting for elasticsearch"
until docker compose exec -T elasticsearch curl -sSf http://localhost:9200 >/dev/null; do
	sleep 2
done

echo "[4/12] Dropping existing elasticsearch schema (if any)"
yes | ../../pelias elastic drop || true

echo "[5/12] Creating elasticsearch schema"
../../pelias elastic create

echo "[6/12] Staging local OSM extract"
mkdir -p ./data/openstreetmap
if [ -f "./stuttgart-regbez-260228.osm.pbf" ]; then
	cp -f ./stuttgart-regbez-260228.osm.pbf ./data/openstreetmap/
fi

echo "[7/12] Downloading WOF"
../../pelias download wof

echo "[8/12] Preparing interpolation source polylines"
../../pelias prepare polylines

echo "[9/12] Preparing placeholder"
../../pelias prepare placeholder

echo "[10/12] Preparing interpolation"
../../pelias prepare interpolation

echo "[11/12] Importing OSM + WOF + polylines"
../../pelias import osm
../../pelias import wof
../../pelias import polylines

echo "[12/12] Starting full stack"
../../pelias compose up

echo "Completed. API should be available at: http://localhost:4500"
