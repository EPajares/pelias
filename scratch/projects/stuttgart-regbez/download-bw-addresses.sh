#!/usr/bin/env bash

set -euo pipefail

# Download all Baden-Württemberg INSPIRE addresses from the LGL WFS service.
#
# Usage:
#   cd tools/pelias-germany-no-oa/pelias-docker/projects/stuttgart-regbez
#   ./download-bw-addresses.sh
#
# Optional environment overrides:
#   OUT_DIR=./data/bw-addresses-gml
#   COUNT=15000
#   START_INDEX=0

WFS_URL="https://owsproxy.lgl-bw.de/owsproxy/wfs/WFS_INSP_BW_Adr_Hauskoord_ALKIS"
TYPE_NAME="ad:Address"
SRS_NAME="EPSG:4258"

OUT_DIR="${OUT_DIR:-./data/bw-addresses-gml}"
COUNT="${COUNT:-15000}"
START_INDEX="${START_INDEX:-0}"
STATE_FILE="${OUT_DIR}/.next_start_index"
MAX_ATTEMPTS_PER_BATCH="${MAX_ATTEMPTS_PER_BATCH:-5}"

mkdir -p "${OUT_DIR}"

if [[ -f "${STATE_FILE}" && "${START_INDEX}" == "0" ]]; then
	START_INDEX="$(cat "${STATE_FILE}")"
	echo "Resuming from saved startIndex=${START_INDEX}"
fi

if ! [[ "${COUNT}" =~ ^[0-9]+$ ]] || ! [[ "${START_INDEX}" =~ ^[0-9]+$ ]]; then
	echo "COUNT and START_INDEX must be non-negative integers." >&2
	exit 1
fi

echo "Output directory: ${OUT_DIR}"
echo "Batch size (count): ${COUNT}"
echo "Starting at startIndex: ${START_INDEX}"

current_start="${START_INDEX}"
downloaded_batches=0

while true; do
	bundle_name="batch_$(printf '%09d' "${current_start}").gml"
	bundle_path="${OUT_DIR}/${bundle_name}"
	tmp_path="${bundle_path}.tmp"

	echo "Downloading startIndex=${current_start} -> ${bundle_name}"

	attempt=1
	while true; do
		rm -f "${tmp_path}"
		curl -sS -f -G "${WFS_URL}" \
			--retry 5 \
			--retry-all-errors \
			--retry-delay 2 \
			--connect-timeout 20 \
			--max-time 600 \
			--data-urlencode "service=WFS" \
			--data-urlencode "version=2.0.0" \
			--data-urlencode "request=GetFeature" \
			--data-urlencode "typeNames=${TYPE_NAME}" \
			--data-urlencode "count=${COUNT}" \
			--data-urlencode "startIndex=${current_start}" \
			--data-urlencode "srsName=${SRS_NAME}" \
			--data-urlencode "outputFormat=application/gml+xml; version=3.2" \
			-o "${tmp_path}" || true

		if [[ -s "${tmp_path}" ]]; then
			break
		fi

		if (( attempt >= MAX_ATTEMPTS_PER_BATCH )); then
			echo "Failed to download non-empty response for startIndex=${current_start} after ${MAX_ATTEMPTS_PER_BATCH} attempts." >&2
			exit 1
		fi

		echo "Retrying startIndex=${current_start} (attempt ${attempt}/${MAX_ATTEMPTS_PER_BATCH})"
		attempt="$((attempt + 1))"
		sleep 3
	done

	if grep -q "ExceptionReport" "${tmp_path}"; then
		echo "WFS returned an ExceptionReport at startIndex=${current_start}." >&2
		rm -f "${tmp_path}"
		exit 1
	fi

	member_count="$(grep -c "<wfs:member>" "${tmp_path}" || true)"
	if [[ "${member_count}" == "0" ]]; then
		echo "No members returned at startIndex=${current_start}. Download complete."
		rm -f "${tmp_path}"
		break
	fi

	mv "${tmp_path}" "${bundle_path}"
	echo "Saved ${bundle_name} (${member_count} features)"

	current_start="$((current_start + COUNT))"
	echo "${current_start}" > "${STATE_FILE}"
	downloaded_batches="$((downloaded_batches + 1))"
done

echo "Done. New batches in this run: ${downloaded_batches}"
echo "Files are in: ${OUT_DIR}"
