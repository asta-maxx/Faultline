#!/usr/bin/env bash
# ==============================================================================
# dump_graph.sh — Trigger BGSAVE, wait for completion, and export dump.rdb
# FalkorDB Persistence: https://docs.falkordb.com/configuration.html
# Working directory: /var/lib/falkordb/data
# Dump file: dump.rdb
# ==============================================================================
set -euo pipefail

CONTAINER_NAME="${FALKOR_CONTAINER:-faultline-falkordb}"
OUTPUT_DIR="${1:-data}"
OUTPUT_FILE="${OUTPUT_DIR}/dump.rdb"

mkdir -p "${OUTPUT_DIR}"

echo "==> Triggering BGSAVE on FalkorDB container '${CONTAINER_NAME}'..."
docker exec "${CONTAINER_NAME}" redis-cli bgsave

echo "==> Waiting for background save to complete..."
while true; do
  IN_PROGRESS=$(docker exec "${CONTAINER_NAME}" redis-cli info persistence | grep "^rdb_bgsave_in_progress:" | tr -d '\r' | cut -d':' -f2)
  if [ "${IN_PROGRESS}" = "0" ]; then
    break
  fi
  sleep 1
done

echo "==> Background save completed. Copying dump.rdb to ${OUTPUT_FILE}..."
docker cp "${CONTAINER_NAME}:/var/lib/falkordb/data/dump.rdb" "${OUTPUT_FILE}"

FILE_SIZE=$(wc -c < "${OUTPUT_FILE}" | tr -d ' ')
echo "==> Export successful: ${OUTPUT_FILE} (${FILE_SIZE} bytes)"
