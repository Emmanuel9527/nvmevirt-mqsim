#!/usr/bin/env bash
set -euo pipefail

RESULT_DIR="${RESULT_DIR:-/home/emmanuel/projects/DiskANN_cpp/results/read_size_sensitivity}"
REAL_DEVICE="${REAL_DEVICE:-/dev/nvme0n1p2}"
SIM_DEVICE="${SIM_DEVICE:-/dev/nvme1n1}"
RUN_REAL="${RUN_REAL:-1}"
RUN_SIM="${RUN_SIM:-1}"
REAL_REPEATS="${REAL_REPEATS:-10}"
SIM_REPEATS="${SIM_REPEATS:-1}"
BS_VALUES="${BS_VALUES:-4k 8k 16k 32k}"
QD="${QD:-16}"
SIZE="${SIZE:-6G}"
RUNTIME="${RUNTIME:-20}"
WARMUP="${WARMUP:-3}"
IOENGINE="${IOENGINE:-libaio}"
RANDSEED="${RANDSEED:-12345}"
DROP_CACHES_BEFORE_RUN="${DROP_CACHES_BEFORE_RUN:-1}"
CACHE_WASH_FILE="${CACHE_WASH_FILE:-}"
CACHE_WASH_RUNTIME="${CACHE_WASH_RUNTIME:-0}"
CACHE_WASH_IODEPTH="${CACHE_WASH_IODEPTH:-32}"
CACHE_WASH_BS="${CACHE_WASH_BS:-4k}"

RAW_CSV="${RAW_CSV:-${RESULT_DIR}/read_size_sensitivity_raw.csv}"
SUMMARY_CSV="${SUMMARY_CSV:-${RESULT_DIR}/read_size_sensitivity_summary.csv}"
SUMMARY_TXT="${SUMMARY_TXT:-${RESULT_DIR}/read_size_sensitivity_summary.txt}"

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
    --ioengine="$IOENGINE" \
    --iodepth="$CACHE_WASH_IODEPTH" \
    --direct=1 \
    --numjobs=1 \
    --runtime="$CACHE_WASH_RUNTIME" \
    --time_based=1 \
    --group_reporting >/dev/null
}

run_one() {
  local fio_name="$1"
  local device="$2"
  local bs="$3"
  local out_json="$4"

  if [[ ! -b "$device" ]]; then
    echo "Missing block device for ${fio_name}: $device" >&2
    exit 1
  fi

  echo
  echo "===== ${fio_name}: randread bs=${bs} qd=${QD} size=${SIZE} runtime=${RUNTIME}s ====="
  drop_os_caches
  wash_ssd_cache
  drop_os_caches

  "${SUDO[@]}" fio \
    --name="$fio_name" \
    --filename="$device" \
    --readonly \
    --rw=randread \
    --bs="$bs" \
    --size="$SIZE" \
    --ioengine="$IOENGINE" \
    --iodepth="$QD" \
    --direct=1 \
    --numjobs=1 \
    --runtime="$RUNTIME" \
    --ramp_time="$WARMUP" \
    --time_based=1 \
    --group_reporting=1 \
    --random_distribution=random \
    --norandommap=1 \
    --randrepeat=1 \
    --randseed="$RANDSEED" \
    --output-format=json \
    --output="$out_json"
}

summarize_json() {
  local target="$1"
  local repeat="$2"
  local bs="$3"
  local json_file="$4"

  python3 - "$target" "$repeat" "$bs" "$QD" "$json_file" <<'PY'
import json
import sys

target, repeat, bs, qd, path = sys.argv[1:6]
with open(path) as f:
    data = json.load(f)

job = data["jobs"][0]
read = job["read"]
lat = read.get("clat_ns") or read.get("lat_ns")
p = lat.get("percentile", {})

def ns_to_us(v):
    return float(v) / 1000.0

def pct(name):
    return ns_to_us(p.get(name, 0.0))

print(",".join([
    target,
    repeat,
    bs,
    qd,
    f'{read.get("iops", 0.0):.2f}',
    f'{read.get("bw", 0.0) / 1024.0:.2f}',
    str(read.get("io_bytes", 0)),
    str(read.get("total_ios", 0)),
    f'{ns_to_us(lat.get("mean", 0.0)):.2f}',
    f'{ns_to_us(lat.get("stddev", 0.0)):.2f}',
    f'{pct("50.000000"):.2f}',
    f'{pct("90.000000"):.2f}',
    f'{pct("99.000000"):.2f}',
    f'{pct("99.900000"):.2f}',
    f'{pct("99.990000"):.2f}',
    f'{ns_to_us(lat.get("max", 0.0)):.2f}',
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
    "iops", "bw_mib_s", "io_bytes", "total_ios", "mean_us", "stddev_us",
    "p50_us", "p90_us", "p99_us", "p999_us", "p9999_us", "max_us",
]
groups = {}
for row in rows:
    groups.setdefault((row["target"], row["bs"], int(row["qd"])), []).append(row)

def bs_order(bs):
    unit = bs[-1].lower()
    num = float(bs[:-1])
    scale = {"k": 1024, "m": 1024 * 1024, "g": 1024 * 1024 * 1024}.get(unit, 1)
    return int(num * scale)

with open(out_path, "w", newline="") as f:
    fieldnames = ["target", "bs", "qd", "repeats"]
    for key in keys:
        fieldnames.extend([key, f"{key}_std"])
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for (target, bs, qd), group in sorted(groups.items(), key=lambda item: (item[0][0], bs_order(item[0][1]))):
        out = {"target": target, "bs": bs, "qd": qd, "repeats": len(group)}
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
print("Read-size sensitivity benchmark average:")
print(f'{"Target":>10} {"BS":>6} {"QD":>5} {"Repeats":>8} {"IOPS":>12} {"BW(MiB/s)":>12} {"Mean(us)":>12} {"MeanStd":>10} {"P50":>10} {"P90":>10} {"P99":>10} {"P999":>10} {"P9999":>10} {"Max(us)":>12}')
print("=" * 154)
for r in rows:
    print(
        f'{r["target"]:>10} {r["bs"]:>6} {r["qd"]:>5} {r["repeats"]:>8} {r["iops"]:>12} {r["bw_mib_s"]:>12} '
        f'{r["mean_us"]:>12} {r["mean_us_std"]:>10} {r["p50_us"]:>10} {r["p90_us"]:>10} '
        f'{r["p99_us"]:>10} {r["p999_us"]:>10} {r["p9999_us"]:>10} {r["max_us"]:>12}'
    )
PY
}

print_raw_tables() {
  python3 - "$RAW_CSV" <<'PY'
import csv
import sys

rows = list(csv.DictReader(open(sys.argv[1], newline="")))
groups = {}
for row in rows:
    groups.setdefault((row["target"], int(row["repeat"])), []).append(row)

def bs_order(bs):
    unit = bs[-1].lower()
    num = float(bs[:-1])
    return int(num * {"k": 1024, "m": 1024 * 1024, "g": 1024 * 1024 * 1024}.get(unit, 1))

for (target, repeat), group in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1])):
    print()
    print(f"Read-size sensitivity table: {target} repeat {repeat}")
    print(f'{"Target":>10} {"Rep":>5} {"BS":>6} {"QD":>5} {"IOPS":>12} {"BW(MiB/s)":>12} {"Mean(us)":>12} {"Std(us)":>10} {"P50":>10} {"P90":>10} {"P99":>10} {"P999":>10} {"P9999":>10} {"Max(us)":>12}')
    print("=" * 154)
    for r in sorted(group, key=lambda row: bs_order(row["bs"])):
        print(
            f'{r["target"]:>10} {r["repeat"]:>5} {r["bs"]:>6} {r["qd"]:>5} {r["iops"]:>12} {r["bw_mib_s"]:>12} '
            f'{r["mean_us"]:>12} {r["stddev_us"]:>10} {r["p50_us"]:>10} {r["p90_us"]:>10} '
            f'{r["p99_us"]:>10} {r["p999_us"]:>10} {r["p9999_us"]:>10} {r["max_us"]:>12}'
        )
PY
}

require_cmd fio
mkdir -p "$RESULT_DIR"

echo "target,repeat,bs,qd,iops,bw_mib_s,io_bytes,total_ios,mean_us,stddev_us,p50_us,p90_us,p99_us,p999_us,p9999_us,max_us" > "$RAW_CSV"

for bs in ${BS_VALUES}; do
  if [[ "$RUN_REAL" == "1" ]]; then
    for repeat in $(seq 1 "$REAL_REPEATS"); do
      json_file="${RESULT_DIR}/real_ssd_repeat${repeat}_bs${bs}_qd${QD}.json"
      run_one "real_ssd_repeat${repeat}_bs${bs}_qd${QD}" "$REAL_DEVICE" "$bs" "$json_file"
      summarize_json "real_ssd" "$repeat" "$bs" "$json_file" >> "$RAW_CSV"
    done
  fi

  if [[ "$RUN_SIM" == "1" ]]; then
    for repeat in $(seq 1 "$SIM_REPEATS"); do
      json_file="${RESULT_DIR}/sim_ssd_repeat${repeat}_bs${bs}_qd${QD}.json"
      run_one "sim_ssd_repeat${repeat}_bs${bs}_qd${QD}" "$SIM_DEVICE" "$bs" "$json_file"
      summarize_json "sim_ssd" "$repeat" "$bs" "$json_file" >> "$RAW_CSV"
    done
  fi
done

aggregate_raw_csv
echo
print_table | tee "$SUMMARY_TXT"
print_raw_tables | tee -a "$SUMMARY_TXT"

if [[ -f "$(dirname "$0")/plot_read_size_sensitivity_benchmark.py" ]]; then
  python3 "$(dirname "$0")/plot_read_size_sensitivity_benchmark.py" "$SUMMARY_CSV" "$RESULT_DIR"
fi

echo
echo "Saved:"
echo "  $RAW_CSV"
echo "  $SUMMARY_CSV"
echo "  $SUMMARY_TXT"
echo "  ${RESULT_DIR}/read_size_sensitivity_mean_latency.png"
echo "  ${RESULT_DIR}/read_size_sensitivity_tail_latency.png"
echo "  ${RESULT_DIR}/read_size_sensitivity_bandwidth.png"
