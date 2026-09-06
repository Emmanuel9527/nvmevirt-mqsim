#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="${ROOT_DIR}/scripts"
BENCH_SRC="${SCRIPT_DIR}/batch_randread_bench.c"
BENCH_BIN="${BENCH_BIN:-/tmp/batch_randread_bench}"

RESULT_DIR="${RESULT_DIR:-/dev/shm/nvmevirt_batch_blktrace_work}"
TRACE_DIR="${TRACE_DIR:-${RESULT_DIR}/blktrace}"
FINAL_RESULT_DIR="${FINAL_RESULT_DIR:-/home/emmanuel/projects/nvmevirt-mqsim/results/batch_aio_blktrace}"
FINAL_BLOCK_SUMMARY_DIR="${FINAL_BLOCK_SUMMARY_DIR:-${FINAL_RESULT_DIR}/block_layer_summaries}"

REAL_DEVICE="${REAL_DEVICE:-/dev/nvme0n1p2}"
REAL_BLOCK_DEVICE="${REAL_BLOCK_DEVICE:-/dev/nvme0n1}"
SIM_DEVICE="${SIM_DEVICE:-/dev/nvme1n2}"
SIM_BLOCK_DEVICE="${SIM_BLOCK_DEVICE:-$SIM_DEVICE}"

RUN_REAL="${RUN_REAL:-0}"
RUN_SIM="${RUN_SIM:-1}"
REAL_REPEATS="${REAL_REPEATS:-10}"
SIM_REPEATS="${SIM_REPEATS:-1}"

BS="${BS:-4k}"
BATCH_SIZE="${BATCH_SIZE:-16}"
BATCH_SIZES="${BATCH_SIZES:-$BATCH_SIZE}"
SIZE="${SIZE:-6G}"
RUNTIME="${RUNTIME:-20}"
WARMUP="${WARMUP:-3}"
GAP_US="${GAP_US:-0}"
RANDSEED="${RANDSEED:-12345}"
DROP_CACHES_BEFORE_RUN="${DROP_CACHES_BEFORE_RUN:-1}"
CACHE_WASH_FILE="${CACHE_WASH_FILE:-}"
CACHE_WASH_RUNTIME="${CACHE_WASH_RUNTIME:-0}"
CACHE_WASH_IODEPTH="${CACHE_WASH_IODEPTH:-32}"
CACHE_WASH_BS="${CACHE_WASH_BS:-4k}"
ALLOW_TRACE_OUTPUT_ON_TRACED_DEVICE="${ALLOW_TRACE_OUTPUT_ON_TRACED_DEVICE:-0}"
KEEP_TRACE_RAW="${KEEP_TRACE_RAW:-0}"
BLOCK_TRACE_PLOTS="${BLOCK_TRACE_PLOTS:-0}"

RAW_CSV="${RAW_CSV:-${RESULT_DIR}/batch_randread_blktrace_raw.csv}"
SUMMARY_CSV="${SUMMARY_CSV:-${RESULT_DIR}/batch_randread_blktrace_summary.csv}"
SUMMARY_TXT="${SUMMARY_TXT:-${RESULT_DIR}/batch_randread_blktrace_summary.txt}"

SUDO=()
if [[ "${EUID}" -ne 0 ]]; then
  SUDO=(sudo)
fi

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
  local traced_parent

  [[ -z "$source_name" ]] && return 1
  traced_parent="$(device_parent_name "$source_name")"

  [[ "$source_name" == "$traced_name" ]] && return 0
  [[ -n "$traced_parent" && "$traced_parent" == "$traced_name" ]] && return 0
  return 1
}

reject_output_on_traced_device() {
  local path="$1"
  local label="$2"
  local traced_device="$3"
  local source_name traced_name

  if [[ "$ALLOW_TRACE_OUTPUT_ON_TRACED_DEVICE" == "1" ]]; then
    return
  fi

  source_name="$(path_source_device_name "$path")"
  traced_name="$(device_name "$traced_device")"
  if source_is_traced_device "$source_name" "$traced_name"; then
    echo "$label is on the traced device: $path" >&2
    echo "  $label source device: ${source_name}" >&2
    echo "  traced block device: ${traced_device}" >&2
    echo "Use RESULT_DIR on tmpfs, e.g. /dev/shm/nvmevirt_batch_blktrace." >&2
    exit 1
  fi
}

drop_os_caches() {
  if [[ "$DROP_CACHES_BEFORE_RUN" != "1" ]]; then
    return
  fi

  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
}

wash_ssd_cache() {
  if [[ -z "$CACHE_WASH_FILE" || "$CACHE_WASH_RUNTIME" == "0" ]]; then
    return
  fi

  if [[ ! -f "$CACHE_WASH_FILE" ]]; then
    echo "Missing CACHE_WASH_FILE: $CACHE_WASH_FILE" >&2
    exit 1
  fi

  fio \
    --name=ssd-cache-wash-before-batch-blktrace \
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

compile_bench() {
  require_cmd gcc
  gcc -O2 -Wall -Wextra "$BENCH_SRC" -o "$BENCH_BIN" -lm
}

stop_blktrace() {
  local pid="${1:-}"
  if [[ -n "$pid" ]]; then
    sudo kill -INT "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
  fi
}

append_run_csv() {
  local target="$1"
  local repeat="$2"
  local run_csv="$3"

  python3 - "$target" "$repeat" "$run_csv" <<'PY'
import csv
import sys

target, repeat, path = sys.argv[1:4]
row = next(csv.DictReader(open(path, newline="")))
print(",".join([
    target,
    repeat,
    row["bs"],
    row["batch_size"],
    row["gap_us"],
    row["runtime_s"],
    row["warmup_s"],
    row["total_ios"],
    row["total_batches"],
    row["iops"],
    row["bw_mib_s"],
    row["io_mean_us"],
    row["io_stddev_us"],
    row["io_p50_us"],
    row["io_p90_us"],
    row["io_p99_us"],
    row["io_p999_us"],
    row["io_p9999_us"],
    row["io_max_us"],
    row["batch_first_mean_us"],
    row["batch_first_p50_us"],
    row["batch_first_p90_us"],
    row["batch_first_p99_us"],
    row["batch_first_p999_us"],
    row["batch_first_max_us"],
    row["batch_mean_us"],
    row["batch_p50_us"],
    row["batch_p90_us"],
    row["batch_p99_us"],
    row["batch_p999_us"],
    row["batch_max_us"],
    row["batch_spread_mean_us"],
    row["batch_spread_p50_us"],
    row["batch_spread_p90_us"],
    row["batch_spread_p99_us"],
    row["batch_spread_p999_us"],
    row["batch_spread_max_us"],
]))
PY
}

aggregate_raw_csv() {
  python3 - "$RAW_CSV" "$SUMMARY_CSV" <<'PY'
import csv
import statistics
import sys

raw_path, out_path = sys.argv[1:3]
rows = list(csv.DictReader(open(raw_path, newline="")))
keys = [
    "total_ios", "total_batches", "iops", "bw_mib_s", "io_mean_us", "io_stddev_us",
    "io_p50_us", "io_p90_us", "io_p99_us", "io_p999_us", "io_p9999_us", "io_max_us",
    "batch_first_mean_us", "batch_first_p50_us", "batch_first_p90_us",
    "batch_first_p99_us", "batch_first_p999_us", "batch_first_max_us",
    "batch_mean_us", "batch_p50_us", "batch_p90_us", "batch_p99_us", "batch_p999_us",
    "batch_max_us",
    "batch_spread_mean_us", "batch_spread_p50_us", "batch_spread_p90_us",
    "batch_spread_p99_us", "batch_spread_p999_us", "batch_spread_max_us",
]
groups = {}
for row in rows:
    groups.setdefault((row["target"], int(row["batch_size"])), []).append(row)

with open(out_path, "w", newline="") as f:
    fieldnames = ["target", "batch_size", "bs", "gap_us", "repeats"]
    for key in keys:
        fieldnames.extend([key, f"{key}_std"])
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for (target, batch_size), group in sorted(groups.items(), key=lambda item: item[0]):
        out = {
            "target": target,
            "batch_size": batch_size,
            "bs": group[0]["bs"],
            "gap_us": group[0]["gap_us"],
            "repeats": len(group),
        }
        for key in keys:
            values = [float(row[key]) for row in group]
            out[key] = f"{statistics.fmean(values):.2f}"
            out[f"{key}_std"] = f"{statistics.stdev(values):.2f}" if len(values) > 1 else "0.00"
        writer.writerow(out)
PY
}

print_table() {
  python3 - "$SUMMARY_CSV" <<'PY'
import csv
import sys

rows = list(csv.DictReader(open(sys.argv[1], newline="")))
print("Batch 4KB uniform random read benchmark average:")
print(f'{"Target":>10} {"Batch":>6} {"BS":>8} {"Gap(us)":>8} {"Repeats":>8} {"IOPS":>12} {"MeanIO(us)":>12} {"First(us)":>12} {"BatchMean":>12} {"Spread(us)":>12} {"BatchP999":>12}')
print("=" * 142)
for r in rows:
    print(
        f'{r["target"]:>10} {r["batch_size"]:>6} {r["bs"]:>8} {r["gap_us"]:>8} {r["repeats"]:>8} '
        f'{r["iops"]:>12} {r["io_mean_us"]:>12} {r["batch_first_mean_us"]:>12} '
        f'{r["batch_mean_us"]:>12} {r["batch_spread_mean_us"]:>12} {r["batch_p999_us"]:>12}'
    )
PY
}

run_one_with_trace() {
  local target="$1"
  local repeat="$2"
  local device="$3"
  local block_device="$4"
  local batch_size="$5"
  local seed="$6"
  local run_label="${target}_repeat${repeat}_batch${batch_size}_bs${BS}_gap${GAP_US}"
  local run_csv="${RESULT_DIR}/${run_label}.csv"
  local final_run_csv="${FINAL_RESULT_DIR}/${run_label}.csv"
  local trace_prefix="${TRACE_DIR}/${run_label}.blktrace"
  local parsed_bin="${TRACE_DIR}/${run_label}.blkparse.bin"
  local btt_prefix="${TRACE_DIR}/${run_label}.btt"
  local btt_data_prefix="${TRACE_DIR}/${run_label}.btt_data"
  local btt_plot_dir="${TRACE_DIR}/${run_label}.plots"
  local btt_summary_csv="${btt_plot_dir}/${run_label}.btt_latency_summary.csv"
  local final_btt_summary_csv="${FINAL_BLOCK_SUMMARY_DIR}/${run_label}.btt_latency_summary.csv"
  local blktrace_pid=""
  local plot_arg=()

  require_block_device "$device"
  require_block_device "$block_device"
  reject_output_on_traced_device "$RESULT_DIR" "RESULT_DIR" "$block_device"
  reject_output_on_traced_device "$TRACE_DIR" "TRACE_DIR" "$block_device"

  mkdir -p "$btt_plot_dir"
  rm -f "${trace_prefix}".* "$parsed_bin" "${btt_prefix}".* "${btt_data_prefix}".*
  rm -rf "$btt_plot_dir"
  mkdir -p "$btt_plot_dir"

  echo
  echo "===== ${run_label}: batch randread with block-layer trace ====="
  echo "  device=${device}"
  echo "  block_device=${block_device}"

  drop_os_caches
  wash_ssd_cache
  drop_os_caches

  sudo blktrace -d "$block_device" -D "$TRACE_DIR" -o "${run_label}.blktrace" &
  blktrace_pid="$!"
  sleep 1

  set +e
  "${SUDO[@]}" "$BENCH_BIN" \
    --filename "$device" \
    --bs "$BS" \
    --batch-size "$batch_size" \
    --size "$SIZE" \
    --runtime "$RUNTIME" \
    --warmup "$WARMUP" \
    --seed "$seed" \
    --gap-us "$GAP_US" \
    --csv "$run_csv"
  bench_status="$?"
  set -e

  stop_blktrace "$blktrace_pid"
  blktrace_pid=""

  if [[ "$bench_status" -ne 0 ]]; then
    echo "Batch benchmark failed for ${run_label}" >&2
    exit "$bench_status"
  fi

  append_run_csv "$target" "$repeat" "$run_csv" >> "$RAW_CSV"
  cp "$run_csv" "$final_run_csv"

  blkparse -i "$trace_prefix" -d "$parsed_bin" >/dev/null
  btt \
    -i "$parsed_bin" \
    -o "$btt_prefix" \
    -z "${btt_data_prefix}.q2d" \
    -l "${btt_data_prefix}.d2c" \
    -q "${btt_data_prefix}.q2c" \
    -Q "${btt_data_prefix}.aqd" \
    >/dev/null

  if [[ "$BLOCK_TRACE_PLOTS" != "1" ]]; then
    plot_arg=(--no-plots)
  fi

  "$SCRIPT_DIR/summarize_btt_latencies.py" \
    --run-label "$run_label" \
    --output-dir "$btt_plot_dir" \
    --q2d-glob "${btt_data_prefix}.q2d*" \
    --d2c-glob "${btt_data_prefix}.d2c*" \
    --q2c-glob "${btt_data_prefix}.q2c*" \
    --aqd-glob "${btt_data_prefix}.aqd*" \
    "${plot_arg[@]}" \
    >/dev/null

  blkparse -i "$trace_prefix" 2>/dev/null | \
    "$SCRIPT_DIR/summarize_blkparse_sizes.py" \
      --run-label "$run_label" \
      --output-dir "$btt_plot_dir" \
      >/dev/null

  cp "$btt_summary_csv" "$final_btt_summary_csv"

  echo "Saved block-layer latency summary:"
  echo "  ${final_btt_summary_csv}"

  if [[ "$KEEP_TRACE_RAW" != "1" ]]; then
    rm -f "${trace_prefix}".* "$parsed_bin" "${btt_prefix}".* "${btt_data_prefix}".*
  fi
}

require_cmd python3
require_cmd gcc
require_cmd blktrace
require_cmd blkparse
require_cmd btt
compile_bench
mkdir -p "$RESULT_DIR" "$TRACE_DIR" "$FINAL_RESULT_DIR" "$FINAL_BLOCK_SUMMARY_DIR"

echo "target,repeat,bs,batch_size,gap_us,runtime_s,warmup_s,total_ios,total_batches,iops,bw_mib_s,io_mean_us,io_stddev_us,io_p50_us,io_p90_us,io_p99_us,io_p999_us,io_p9999_us,io_max_us,batch_first_mean_us,batch_first_p50_us,batch_first_p90_us,batch_first_p99_us,batch_first_p999_us,batch_first_max_us,batch_mean_us,batch_p50_us,batch_p90_us,batch_p99_us,batch_p999_us,batch_max_us,batch_spread_mean_us,batch_spread_p50_us,batch_spread_p90_us,batch_spread_p99_us,batch_spread_p999_us,batch_spread_max_us" > "$RAW_CSV"

if [[ "$RUN_REAL" == "1" ]]; then
  for batch_size in $BATCH_SIZES; do
    for repeat in $(seq 1 "$REAL_REPEATS"); do
      run_one_with_trace "real_ssd" "$repeat" "$REAL_DEVICE" "$REAL_BLOCK_DEVICE" "$batch_size" "$((RANDSEED + repeat))"
    done
  done
fi

if [[ "$RUN_SIM" == "1" ]]; then
  for batch_size in $BATCH_SIZES; do
    for repeat in $(seq 1 "$SIM_REPEATS"); do
      run_one_with_trace "sim_ssd" "$repeat" "$SIM_DEVICE" "$SIM_BLOCK_DEVICE" "$batch_size" "$((RANDSEED + repeat))"
    done
  done
fi

aggregate_raw_csv
print_table | tee "$SUMMARY_TXT"
if [[ "$SUMMARY_CSV" != "${FINAL_RESULT_DIR}/$(basename "$SUMMARY_CSV")" ]]; then
  cp "$SUMMARY_CSV" "${FINAL_RESULT_DIR}/$(basename "$SUMMARY_CSV")"
fi
if [[ "$SUMMARY_TXT" != "${FINAL_RESULT_DIR}/$(basename "$SUMMARY_TXT")" ]]; then
  cp "$SUMMARY_TXT" "${FINAL_RESULT_DIR}/$(basename "$SUMMARY_TXT")"
fi
if [[ "$RAW_CSV" != "${FINAL_RESULT_DIR}/$(basename "$RAW_CSV")" ]]; then
  cp "$RAW_CSV" "${FINAL_RESULT_DIR}/$(basename "$RAW_CSV")"
fi

python3 "$SCRIPT_DIR/plot_batch_randread_benchmark.py" "$SUMMARY_CSV" "$FINAL_RESULT_DIR"

echo
echo "Done."
echo "Benchmark summary:"
echo "  ${FINAL_RESULT_DIR}/$(basename "$RAW_CSV")"
echo "  ${FINAL_RESULT_DIR}/$(basename "$SUMMARY_CSV")"
echo "  ${FINAL_RESULT_DIR}/$(basename "$SUMMARY_TXT")"
echo
echo "Block-layer latency summaries:"
find "$FINAL_BLOCK_SUMMARY_DIR" -name '*.btt_latency_summary.csv' -print | sort
echo
echo "Block-layer plots:"
find "$TRACE_DIR" \( -name '*.png' -o -name '*_hist.svg' \) -print | sort
