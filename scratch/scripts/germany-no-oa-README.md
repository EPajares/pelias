# Local Pelias Germany (No OpenAddresses)

This folder contains an isolated Pelias setup for Germany, based on `pelias/docker`, configured without OpenAddresses.

## What is isolated

- Separate compose project name: `pelias_de_nooa`
- No fixed `container_name` values in compose (avoids collisions)
- Dedicated project directory: `pelias-docker/projects/germany-no-oa`
- OpenAddresses removed from `pelias.json`

## Project location

- Pelias framework: `tools/pelias-germany-no-oa/pelias-docker`
- Germany no-OA project: `tools/pelias-germany-no-oa/pelias-docker/projects/germany-no-oa`

## Build and run (no OA)

From repo root:

```bash
chmod +x tools/pelias-germany-no-oa/run-build-no-oa.sh
tools/pelias-germany-no-oa/run-build-no-oa.sh
```

The script runs these data sources/imports:

- `openstreetmap`
- `whosonfirst`
- `placeholder` (built from WOF)
- `polylines` + `interpolation` (for better address interpolation)

It intentionally does **not** run any OpenAddresses download or import commands.

For Germany, the script ensures a polyline file by downloading:

- `https://data.geocode.earth/osm/2022-35/germany-valhalla.polylines.0sv.gz`

to `data/polylines/extract.0sv` before interpolation build/import.

## Query endpoint

After startup:

- API: `http://localhost:4000/v1/search?text=Berlin`

## Stop / cleanup

```bash
cd tools/pelias-germany-no-oa/pelias-docker/projects/germany-no-oa
../../pelias compose down
```
