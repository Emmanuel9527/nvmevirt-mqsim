#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_SRC="${SCRIPT_DIR}/batch_randread_bench.c"
BENCH_BIN="${BENCH_BIN:-/tmp/batch_randread_bench}"
RESULT_DIR="${RESULT_DIR:-/home/emmanuel/projects/DiskANN_cpp/results/batch_randread}"
REAL_DEVICE="${REAL_DEVICE:-/dev/nvme0n1p2}"
SIM_DEVICE="${SIM_DEVICE:-/dev/nvme1n1}"
RUN_REAL="${RUN_REAL:-1}"
RUN_SIM="${RUN_SIM:-1}"
REAL_REPEATS="${REAL_REPEATS:-10}"
SIM_REPEATS="${SIM_REPEATS:-1}"
BS="${BS:-4k}"
BATCH_SIZE="${BATCH_SIZE:-16}"
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

RAW_CSV="${RAW_CSV:-${RESULT_DIR}/batch_randread_raw.csv}"
SUMMARY_CSV="${SUMMARY_CSV:-${RESULT_DIR}/batch_randread_summary.csv}"
SUMMARY_TXT="${SUMMARY_TXT:-${RESULT_DIR}/batch_randread_summary.txt}"

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
    --name=ssd-cache-wash \
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

run_one() {
  local target="$1"
  local repeat="$2"
  local device="$3"
  local out_csv="$4"
  local seed

  if [[ ! -b "$device" ]]; then
    echo "Missing block device for ${target}: $device" >&2
    exit 1
  fi

  seed=$((RANDSEED + repeat))
  echo
  echo "===== ${target} repeat ${repeat}: batch randread bs=${BS} batch=${BATCH_SIZE} size=${SIZE} runtime=${RUNTIME}s gap=${GAP_US}us ====="
  drop_os_caches
  wash_ssd_cache
  drop_os_caches

  "${SUDO[@]}" "$BENCH_BIN" \
    --filename "$device" \
    --bs "$BS" \
    --batch-size "$BATCH_SIZE" \
    --size "$SIZE" \
    --runtime "$RUNTIME" \
    --warmup "$WARMUP" \
    --seed "$seed" \
    --gap-us "$GAP_US" \
    --csv "$out_csv"
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
    row["batch_mean_us"],
    row["batch_p50_us"],
    row["batch_p90_us"],
    row["batch_p99_us"],
    row["batch_p999_us"],
    row["batch_max_us"],
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
    "batch_mean_us", "batch_p50_us", "batch_p90_us", "batch_p99_us", "batch_p999_us",
    "batch_max_us",
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
print(f'{"Target":>10} {"Batch":>6} {"BS":>8} {"Gap(us)":>8} {"Repeats":>8} {"IOPS":>12} {"MeanIO(us)":>12} {"P50":>10} {"P90":>10} {"P99":>10} {"P999":>10} {"BatchMean":>12} {"BatchP999":>12}')
print("=" * 150)
for r in rows:
    print(
        f'{r["target"]:>10} {r["batch_size"]:>6} {r["bs"]:>8} {r["gap_us"]:>8} {r["repeats"]:>8} '
        f'{r["iops"]:>12} {r["io_mean_us"]:>12} {r["io_p50_us"]:>10} {r["io_p90_us"]:>10} '
        f'{r["io_p99_us"]:>10} {r["io_p999_us"]:>10} {r["batch_mean_us"]:>12} {r["batch_p999_us"]:>12}'
    )
PY
}

require_cmd python3
compile_bench
mkdir -p "$RESULT_DIR"

echo "target,repeat,bs,batch_size,gap_us,runtime_s,warmup_s,total_ios,total_batches,iops,bw_mib_s,io_mean_us,io_stddev_us,io_p50_us,io_p90_us,io_p99_us,io_p999_us,io_p9999_us,io_max_us,batch_mean_us,batch_p50_us,batch_p90_us,batch_p99_us,batch_p999_us,batch_max_us" > "$RAW_CSV"

if [[ "$RUN_REAL" == "1" ]]; then
  for repeat in $(seq 1 "$REAL_REPEATS"); do
    run_csv="${RESULT_DIR}/real_ssd_repeat${repeat}_batch${BATCH_SIZE}_bs${BS}_gap${GAP_US}.csv"
    run_one "real_ssd" "$repeat" "$REAL_DEVICE" "$run_csv"
    append_run_csv "real_ssd" "$repeat" "$run_csv" >> "$RAW_CSV"
  done
fi

if [[ "$RUN_SIM" == "1" ]]; then
  for repeat in $(seq 1 "$SIM_REPEATS"); do
    run_csv="${RESULT_DIR}/sim_ssd_repeat${repeat}_batch${BATCH_SIZE}_bs${BS}_gap${GAP_US}.csv"
    run_one "sim_ssd" "$repeat" "$SIM_DEVICE" "$run_csv"
    append_run_csv "sim_ssd" "$repeat" "$run_csv" >> "$RAW_CSV"
  done
fi

aggregate_raw_csv
echo
print_table | tee "$SUMMARY_TXT"

if [[ -f "${SCRIPT_DIR}/plot_batch_randread_benchmark.py" ]]; then
  python3 "${SCRIPT_DIR}/plot_batch_randread_benchmark.py" "$SUMMARY_CSV" "$RESULT_DIR"
fi

echo
echo "Saved:"
echo "  $RAW_CSV"
echo "  $SUMMARY_CSV"
echo "  $SUMMARY_TXT"
echo "  ${RESULT_DIR}/batch_randread_io_mean_latency.png"
echo "  ${RESULT_DIR}/batch_randread_batch_mean_latency.png"
echo "  ${RESULT_DIR}/batch_randread_iops.png"
