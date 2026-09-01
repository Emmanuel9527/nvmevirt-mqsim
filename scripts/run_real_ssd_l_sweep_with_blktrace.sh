#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISKANN_DIR="${DISKANN_DIR:-/home/emmanuel/projects/DiskANN_cpp}"
RESULT_DIR="${RESULT_DIR:-${DISKANN_DIR}/results/real_ssd_latency_blktrace}"
TRACE_DIR="${TRACE_DIR:-${RESULT_DIR}/blktrace}"

BLOCK_DEVICE="${BLOCK_DEVICE:-/dev/nvme0n1}"
DEVICE="${DEVICE:-/dev/nvme0n1p2}"
L_VALUES="${L_VALUES:-20 40 60 80 100 120}"
W="${W:-16}"
T="${T:-1}"
NUM_NODES_TO_CACHE="${NUM_NODES_TO_CACHE:-0}"
INDEX_VARIANT="${INDEX_VARIANT:-block_shuffle}"
DROP_CACHES_BEFORE_TRACE="${DROP_CACHES_BEFORE_TRACE:-1}"
CACHE_WASH_FILE="${CACHE_WASH_FILE:-/home/emmanuel/projects/data/cache_wash_64g.bin}"
CACHE_WASH_RUNTIME="${CACHE_WASH_RUNTIME:-5}"
CACHE_WASH_IODEPTH="${CACHE_WASH_IODEPTH:-32}"
CACHE_WASH_BS="${CACHE_WASH_BS:-4k}"
ALLOW_TRACE_OUTPUT_ON_TRACED_DEVICE="${ALLOW_TRACE_OUTPUT_ON_TRACED_DEVICE:-0}"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing command: $cmd" >&2
    exit 1
  fi
}

require_block_device() {
  local dev="$1"
  if [[ ! -b "$dev" ]]; then
    echo "Not a block device: $dev" >&2
    exit 1
  fi
}

device_name() {
  basename "$(readlink -f "$1")"
}

device_parent_name() {
  local dev_name="$1"
  lsblk -no PKNAME "/dev/$dev_name" 2>/dev/null | head -n 1
}

path_source_device_name() {
  local path="$1"
  local source

  mkdir -p "$path"
  source="$(findmnt -T "$path" -o SOURCE -n 2>/dev/null || true)"
  if [[ "$source" == /dev/* ]]; then
    device_name "$source"
  fi
}

source_is_traced_device() {
  local source_name="$1"
  local traced_name="$2"
  local iostat_name="$3"
  local source_parent traced_parent iostat_parent

  [[ -z "$source_name" ]] && return 1
  source_parent="$(device_parent_name "$source_name")"
  traced_parent="$(device_parent_name "$traced_name")"
  iostat_parent="$(device_parent_name "$iostat_name")"

  [[ "$source_name" == "$traced_name" ]] && return 0
  [[ "$source_name" == "$iostat_name" ]] && return 0
  [[ -n "$source_parent" && "$source_parent" == "$traced_name" ]] && return 0
  [[ -n "$source_parent" && "$source_parent" == "$iostat_name" ]] && return 0
  [[ -n "$traced_parent" && "$source_name" == "$traced_parent" ]] && return 0
  [[ -n "$iostat_parent" && "$source_name" == "$iostat_parent" ]] && return 0
  return 1
}

reject_output_on_traced_device() {
  local path="$1"
  local label="$2"
  local source_name traced_name iostat_name

  if [[ "$ALLOW_TRACE_OUTPUT_ON_TRACED_DEVICE" == "1" ]]; then
    return
  fi

  source_name="$(path_source_device_name "$path")"
  traced_name="$(device_name "$BLOCK_DEVICE")"
  iostat_name="$(device_name "$DEVICE")"
  if source_is_traced_device "$source_name" "$traced_name" "$iostat_name"; then
    echo "$label is on the traced device: $path" >&2
    echo "  $label source device: ${source_name}" >&2
    echo "  BLOCK_DEVICE: ${BLOCK_DEVICE}" >&2
    echo "  DEVICE: ${DEVICE}" >&2
    echo "Use a tmpfs or another disk for RESULT_DIR and TRACE_DIR." >&2
    exit 1
  fi
}

stop_blktrace() {
  local pid="${1:-}"
  if [[ -n "$pid" ]]; then
    sudo kill -INT "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
  fi
}

drop_os_caches() {
  if [[ "$DROP_CACHES_BEFORE_TRACE" != "1" ]]; then
    return
  fi

  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
}

wash_ssd_cache() {
  if [[ -z "$CACHE_WASH_FILE" ]]; then
    return
  fi

  if [[ ! -f "$CACHE_WASH_FILE" ]]; then
    echo "Missing CACHE_WASH_FILE: $CACHE_WASH_FILE" >&2
    exit 1
  fi
  if ! command -v fio >/dev/null 2>&1; then
    echo "fio is required when CACHE_WASH_FILE is set." >&2
    exit 1
  fi

  fio \
    --name=ssd-cache-wash-before-blktrace \
    --filename="$CACHE_WASH_FILE" \
    --rw=randread \
    --bs="$CACHE_WASH_BS" \
    --ioengine=libaio \
    --iodepth="$CACHE_WASH_IODEPTH" \
    --direct=1 \
    --numjobs=1 \
    --runtime="$CACHE_WASH_RUNTIME" \
    --time_based=1 \
    --group_reporting >/dev/null
}

require_cmd blktrace
require_cmd blkparse
require_cmd btt
require_block_device "$BLOCK_DEVICE"
require_block_device "$DEVICE"

mkdir -p "$RESULT_DIR" "$TRACE_DIR"
reject_output_on_traced_device "$RESULT_DIR" "RESULT_DIR"
reject_output_on_traced_device "$TRACE_DIR" "TRACE_DIR"

echo "Real SSD DiskANN L sweep with blktrace"
echo "  block_device=${BLOCK_DEVICE}"
echo "  iostat_device=${DEVICE}"
echo "  result_dir=${RESULT_DIR}"
echo "  trace_dir=${TRACE_DIR}"
echo "  L_VALUES=${L_VALUES}"
echo

for l_value in ${L_VALUES}; do
  run_label="${INDEX_VARIANT}_L${l_value}_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}"
  trace_prefix="${TRACE_DIR}/${run_label}.blktrace"
  parsed_bin="${TRACE_DIR}/${run_label}.blkparse.bin"
  btt_prefix="${TRACE_DIR}/${run_label}.btt"
  btt_data_prefix="${TRACE_DIR}/${run_label}.btt_data"
  btt_plot_dir="${TRACE_DIR}/${run_label}.plots"
  run_result_dir="${RESULT_DIR}/${run_label}"
  blktrace_pid=""

  mkdir -p "$run_result_dir"
  rm -f "${trace_prefix}".* "$parsed_bin" "${btt_prefix}".* "${btt_data_prefix}".*
  rm -rf "$btt_plot_dir"

  echo
  echo "===== L=${l_value}: cleaning caches before trace ====="
  drop_os_caches
  wash_ssd_cache
  drop_os_caches

  echo
  echo "===== L=${l_value}: starting blktrace ====="
  sudo blktrace -d "$BLOCK_DEVICE" -D "$TRACE_DIR" -o "${run_label}.blktrace" &
  blktrace_pid="$!"
  sleep 2

  echo "===== L=${l_value}: running DiskANN ====="
  set +e
  RESULT_DIR="$run_result_dir" \
  DEVICE="$DEVICE" \
  DROP_CACHES_BEFORE_RUN=0 \
  CACHE_WASH_FILE= \
  L_VALUES="$l_value" \
  W="$W" \
  T="$T" \
  NUM_NODES_TO_CACHE="$NUM_NODES_TO_CACHE" \
  INDEX_VARIANT="$INDEX_VARIANT" \
    "$ROOT_DIR/scripts/run_real_ssd_l_sweep_latency.sh"
  diskann_status="$?"
  set -e

  echo "===== L=${l_value}: stopping blktrace ====="
  stop_blktrace "$blktrace_pid"
  blktrace_pid=""

  if [[ "$diskann_status" -ne 0 ]]; then
    echo "DiskANN run failed for L=${l_value}" >&2
    exit "$diskann_status"
  fi

  echo "===== L=${l_value}: running blkparse/btt ====="
  blkparse -i "$trace_prefix" -d "$parsed_bin" >/dev/null
  btt \
    -i "$parsed_bin" \
    -o "$btt_prefix" \
    -z "${btt_data_prefix}.q2d" \
    -l "${btt_data_prefix}.d2c" \
    -q "${btt_data_prefix}.q2c" \
    -Q "${btt_data_prefix}.aqd" \
    >/dev/null

  "$ROOT_DIR/scripts/summarize_btt_latencies.py" \
    --run-label "$run_label" \
    --output-dir "$btt_plot_dir" \
    --q2d-glob "${btt_data_prefix}.q2d*" \
    --d2c-glob "${btt_data_prefix}.d2c*" \
    --q2c-glob "${btt_data_prefix}.q2c*" \
    --aqd-glob "${btt_data_prefix}.aqd*" \
    >/dev/null

  blkparse -i "$trace_prefix" 2>/dev/null | \
    "$ROOT_DIR/scripts/summarize_blkparse_sizes.py" \
      --run-label "$run_label" \
      --output-dir "$btt_plot_dir" \
      >/dev/null

  echo "Saved:"
  echo "  DiskANN result dir: $run_result_dir"
  echo "  blktrace files:    ${trace_prefix}.*"
  echo "  blkparse binary:   $parsed_bin"
  echo "  btt outputs:       ${btt_prefix}.*"
  echo "  btt latency data:  ${btt_data_prefix}.{q2d,d2c,q2c}*"
  echo "  latency plots:     ${btt_plot_dir}"
done

"$ROOT_DIR/scripts/plot_btt_l_sweep.py" \
  --trace-dir "$TRACE_DIR" \
  --index-variant "$INDEX_VARIANT" \
  --l-values "$L_VALUES" \
  --w "$W" \
  --t "$T" \
  --cache "$NUM_NODES_TO_CACHE" \
  >/dev/null

echo
echo "Done."
echo "Latency tables:"
find "$RESULT_DIR" -name '*.latency_table.txt' -print | sort
echo
echo "BTT avg files:"
find "$TRACE_DIR" -name '*.avg' -print | sort
echo
echo "BTT latency summaries:"
find "$TRACE_DIR" -name '*.btt_latency_summary.csv' -print | sort
echo
echo "BTT latency plots:"
find "$TRACE_DIR" \( -name '*.png' -o -name '*_hist.svg' \) -print | sort
