#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
RESULT_ROOT="${RESULT_ROOT:-/home/emmanuel/projects/DiskANN_cpp/results/real_ssd_latency_repeats}"
REPEATS="${REPEATS:-5}"
L_VALUES="${L_VALUES:-20 40 60 80 100 120}"
W="${W:-16}"
T="${T:-1}"
INDEX_VARIANT="${INDEX_VARIANT:-block_shuffle}"
NUM_NODES_TO_CACHE="${NUM_NODES_TO_CACHE:-0}"

mkdir -p "$RESULT_ROOT"

for repeat_id in $(seq 1 "$REPEATS"); do
  run_dir="${RESULT_ROOT}/run_${repeat_id}"
  echo
  echo "===== Real SSD repeat ${repeat_id}/${REPEATS} ====="
  RESULT_DIR="$run_dir" \
  L_VALUES="$L_VALUES" \
  W="$W" \
  T="$T" \
  INDEX_VARIANT="$INDEX_VARIANT" \
  NUM_NODES_TO_CACHE="$NUM_NODES_TO_CACHE" \
    "$ROOT_DIR/scripts/run_real_ssd_l_sweep_latency.sh"
done

echo
python3 "$ROOT_DIR/scripts/summarize_real_ssd_repeats.py" \
  --result-root "$RESULT_ROOT" \
  --index-variant "$INDEX_VARIANT" \
  --w "$W" \
  --t "$T" \
  --cache "$NUM_NODES_TO_CACHE"
