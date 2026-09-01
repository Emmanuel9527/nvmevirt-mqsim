#!/usr/bin/env bash
set -euo pipefail

DISKANN_DIR="${DISKANN_DIR:-/home/emmanuel/projects/DiskANN_cpp}"
BUILD_DIR="${BUILD_DIR:-${DISKANN_DIR}/build}"
RESULT_DIR="${RESULT_DIR:-${DISKANN_DIR}/results/real_ssd_latency}"
INDEX_DIR="${INDEX_DIR:-/home/emmanuel/projects/data/sift1m_diskann_indexes}"
INDEX_VARIANT="${INDEX_VARIANT:-block_shuffle}"
PREFIX_STEM="${PREFIX_STEM:-sift1m_l2_R64_L100_pq0}"
INDEX_PREFIX="${INDEX_PREFIX:-${INDEX_DIR}/${PREFIX_STEM}_${INDEX_VARIANT}}"
QUERY_FILE="${QUERY_FILE:-/home/emmanuel/projects/data/sift1m/sift_query.fbin}"
GT_FILE="${GT_FILE:-/home/emmanuel/projects/data/sift1m/sift_groundtruth.bin}"
DATA_TYPE="${DATA_TYPE:-float}"
DIST_FN="${DIST_FN:-l2}"
K="${K:-10}"
L_VALUES="${L_VALUES:-20 40 60 80 100 120}"
W="${W:-16}"
T="${T:-1}"
NUM_NODES_TO_CACHE="${NUM_NODES_TO_CACHE:-0}"
USE_SECTOR_CANDIDATES="${USE_SECTOR_CANDIDATES:-0}"
TRACE_SAMPLE_RATE="${TRACE_SAMPLE_RATE:-1}"
TRACE_MAX_QUERIES="${TRACE_MAX_QUERIES:-0}"
DEVICE="${DEVICE:-/dev/nvme0n1p2}"
COLLECT_IOSTAT="${COLLECT_IOSTAT:-1}"
DROP_CACHES_BEFORE_RUN="${DROP_CACHES_BEFORE_RUN:-1}"
CACHE_WASH_FILE="${CACHE_WASH_FILE-/home/emmanuel/projects/data/cache_wash_64g.bin}"
CACHE_WASH_RUNTIME="${CACHE_WASH_RUNTIME:-5}"
CACHE_WASH_IODEPTH="${CACHE_WASH_IODEPTH:-32}"
CACHE_WASH_BS="${CACHE_WASH_BS:-4k}"
COLLECT_NVME_TEMP="${COLLECT_NVME_TEMP:-1}"
TEMP_SAMPLE_INTERVAL="${TEMP_SAMPLE_INTERVAL:-1}"
TEMP_SENSOR_PATH="${TEMP_SENSOR_PATH:-}"

SEARCH_BIN="${SEARCH_BIN:-${BUILD_DIR}/apps/search_disk_index}"
SUMMARY_FILE="${SUMMARY_FILE:-${RESULT_DIR}/${INDEX_VARIANT}_L_sweep_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}.latency_table.txt}"
PERF_SUMMARY_FILE="${PERF_SUMMARY_FILE:-${RESULT_DIR}/${INDEX_VARIANT}_L_sweep_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}.performance_summary.txt}"

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Missing file: $path" >&2
    exit 1
  fi
}

require_exe() {
  local path="$1"
  if [[ ! -x "$path" ]]; then
    echo "Missing executable: $path" >&2
    exit 1
  fi
}

extract_performance_table() {
  local log_file="$1"
  local out_file="$2"

  awk '
    /[[:space:]]L[[:space:]]+Beamwidth[[:space:]]+QPS[[:space:]]+Mean Latency/ {
      capture = 1
      rows = 0
    }
    capture {
      if ($0 ~ /[[:space:]]L[[:space:]]+Beamwidth[[:space:]]+QPS[[:space:]]+Mean Latency/ ||
          $0 ~ /^=+/) {
        print
        next
      }
      if ($1 ~ /^[0-9]+$/) {
        print
        rows++
        next
      }
      if (rows > 0)
        exit
    }
  ' "$log_file" > "$out_file"
}

run_iostat() {
  local device="$1"
  local out_file="$2"

  if [[ "$COLLECT_IOSTAT" != "1" || -z "$device" || ! -b "$device" ]]; then
    return
  fi
  if ! command -v iostat >/dev/null 2>&1; then
    return
  fi

  iostat -x -y "$(basename "$device")" 1 > "$out_file" &
  echo "$!"
}

resolve_block_disk() {
  local device="$1"
  local name sys_path

  name="$(basename "$device")"
  sys_path="/sys/class/block/${name}"
  if [[ ! -e "$sys_path" ]]; then
    return
  fi

  if [[ -f "${sys_path}/partition" ]]; then
    basename "$(readlink -f "${sys_path}/..")"
  else
    basename "$(readlink -f "$sys_path")"
  fi
}

find_nvme_temp_sensor() {
  local device="$1"
  local disk dev_path sensor

  if [[ -n "$TEMP_SENSOR_PATH" ]]; then
    if [[ ! -r "$TEMP_SENSOR_PATH" ]]; then
      echo "TEMP_SENSOR_PATH is not readable: $TEMP_SENSOR_PATH" >&2
      exit 1
    fi
    echo "$TEMP_SENSOR_PATH"
    return
  fi

  disk="$(resolve_block_disk "$device" || true)"
  if [[ -n "$disk" && -e "/sys/class/block/${disk}/device" ]]; then
    dev_path="$(readlink -f "/sys/class/block/${disk}/device")"
    sensor="$(find "${dev_path}/hwmon" -maxdepth 2 -type f -name temp1_input -print -quit 2>/dev/null || true)"
    if [[ -n "$sensor" && -r "$sensor" ]]; then
      echo "$sensor"
      return
    fi
  fi

  for sensor in /sys/class/hwmon/hwmon*/temp1_input; do
    [[ -r "$sensor" ]] || continue
    if [[ "$(cat "$(dirname "$sensor")/name" 2>/dev/null || true)" == "nvme" ]]; then
      local raw
      raw="$(cat "$sensor" 2>/dev/null || true)"
      if [[ "$raw" =~ ^-?[0-9]+$ && "$raw" -lt 0 ]]; then
        continue
      fi
      echo "$sensor"
      return
    fi
  done
}

run_temp_logger() {
  local sensor="$1"
  local out_file="$2"
  local label_file label

  if [[ "$COLLECT_NVME_TEMP" != "1" || -z "$sensor" || ! -r "$sensor" ]]; then
    return
  fi

  label_file="${sensor%_input}_label"
  label="$(cat "$label_file" 2>/dev/null || echo "unknown")"

  (
    local start_ns now_ns raw temp_c
    start_ns="$(date +%s%N)"
    printf "timestamp_ns,elapsed_s,temp_c,sensor,label\n"
    while true; do
      now_ns="$(date +%s%N)"
      raw="$(cat "$sensor" 2>/dev/null || true)"
      if [[ "$raw" =~ ^-?[0-9]+$ ]]; then
        temp_c="$(awk -v raw="$raw" 'BEGIN { printf "%.3f", raw / 1000.0 }')"
        awk -v now="$now_ns" -v start="$start_ns" -v temp="$temp_c" \
            -v sensor="$sensor" -v label="$label" \
            'BEGIN { printf "%s,%.6f,%s,%s,%s\n", now, (now - start) / 1000000000.0, temp, sensor, label }'
      fi
      sleep "$TEMP_SAMPLE_INTERVAL"
    done
  ) > "$out_file" &
  echo "$!"
}

drop_os_caches() {
  if [[ "$DROP_CACHES_BEFORE_RUN" != "1" ]]; then
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

stop_background() {
  local pid="${1:-}"
  if [[ -n "$pid" ]]; then
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
  fi
}

analyze_trace() {
  local trace_csv="$1"
  local perf_file="$2"
  local iostat_file="$3"
  local out_file="$4"

  python3 - "$trace_csv" "$perf_file" "$iostat_file" "$out_file" <<'PY'
import csv
import math
import pathlib
import statistics
import sys

trace_csv, perf_file, iostat_file, out_file = sys.argv[1:5]

def pct(values, q):
    if not values:
        return 0.0
    values = sorted(values)
    idx = int(math.ceil(q * len(values))) - 1
    idx = max(0, min(idx, len(values) - 1))
    return values[idx]

def mean(values):
    return statistics.fmean(values) if values else 0.0

def perf_row(path):
    for line in pathlib.Path(path).read_text(errors="replace").splitlines():
        parts = line.split()
        if parts and parts[0].isdigit():
            return {
                "L": parts[0],
                "QPS": parts[2],
                "MeanLat": parts[3],
                "P999Lat": parts[4],
                "MeanIOs": parts[5],
                "MeanIO_us": parts[6],
                "MeanHops": parts[9],
            }
    return {}

def iostat_summary(path):
    p = pathlib.Path(path)
    if not path or not p.exists() or p.stat().st_size == 0:
        return {
            "aqu": "N/A", "aqu_p50": "N/A", "aqu_p90": "N/A", "aqu_p99": "N/A", "aqu_max": "N/A",
            "rawait": "N/A", "rawait_p50": "N/A", "rawait_p90": "N/A", "rawait_p99": "N/A", "rawait_max": "N/A",
        }

    aqu_values = []
    rawait_values = []
    header = None
    for line in p.read_text(errors="replace").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "Device":
            header = parts
            continue
        if header and len(parts) == len(header):
            row = dict(zip(header, parts))
            try:
                if "aqu-sz" in row:
                    aqu_values.append(float(row["aqu-sz"]))
                if "r_await" in row:
                    rawait_values.append(float(row["r_await"]))
            except ValueError:
                pass
    return {
        "aqu": f"{mean(aqu_values):.2f}" if aqu_values else "N/A",
        "aqu_p50": f"{pct(aqu_values, 0.50):.2f}" if aqu_values else "N/A",
        "aqu_p90": f"{pct(aqu_values, 0.90):.2f}" if aqu_values else "N/A",
        "aqu_p99": f"{pct(aqu_values, 0.99):.2f}" if aqu_values else "N/A",
        "aqu_max": f"{max(aqu_values):.2f}" if aqu_values else "N/A",
        "rawait": f"{mean(rawait_values) * 1000.0:.2f}" if rawait_values else "N/A",
        "rawait_p50": f"{pct(rawait_values, 0.50) * 1000.0:.2f}" if rawait_values else "N/A",
        "rawait_p90": f"{pct(rawait_values, 0.90) * 1000.0:.2f}" if rawait_values else "N/A",
        "rawait_p99": f"{pct(rawait_values, 0.99) * 1000.0:.2f}" if rawait_values else "N/A",
        "rawait_max": f"{max(rawait_values) * 1000.0:.2f}" if rawait_values else "N/A",
    }

rows = []
with open(trace_csv, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            issued = int(row["issued_reads"])
            io_us = float(row["io_us"])
            qid = int(row["query_id"])
            iteration = int(row["iteration"])
        except (KeyError, ValueError):
            continue
        if issued <= 0 or io_us <= 0:
            continue
        rows.append((qid, iteration, issued, io_us))

hop_io = [r[3] for r in rows]
issued_reads = [r[2] for r in rows]
per_query_max = {}
per_query_total = {}
for qid, _, _, io_us in rows:
    per_query_max[qid] = max(per_query_max.get(qid, 0.0), io_us)
    per_query_total[qid] = per_query_total.get(qid, 0.0) + io_us

perf = perf_row(perf_file)
iostat = iostat_summary(iostat_file)

summary = {
    "L": perf.get("L", "unknown"),
    "QPS": perf.get("QPS", "0"),
    "MeanLat": perf.get("MeanLat", "0"),
    "P999Lat": perf.get("P999Lat", "0"),
    "MeanIO_us": perf.get("MeanIO_us", "0"),
    "MeanHops": perf.get("MeanHops", "0"),
    "HopIO_p50": pct(hop_io, 0.50),
    "HopIO_p90": pct(hop_io, 0.90),
    "HopIO_p99": pct(hop_io, 0.99),
    "HopIO_p999": pct(hop_io, 0.999),
    "HopIO_max": max(hop_io) if hop_io else 0.0,
    "QD_avg": mean(issued_reads),
    "QD_p99": pct(issued_reads, 0.99),
    "QD_max": max(issued_reads) if issued_reads else 0,
    "QueryMaxIO_p99": pct(list(per_query_max.values()), 0.99),
    "QueryMaxIO_p999": pct(list(per_query_max.values()), 0.999),
    "QueryMaxIO_max": max(per_query_max.values()) if per_query_max else 0.0,
    "QueryIOsum_p999": pct(list(per_query_total.values()), 0.999),
    "iostat_r_await_us": iostat["rawait"],
    "iostat_r_await_p50_us": iostat["rawait_p50"],
    "iostat_r_await_p90_us": iostat["rawait_p90"],
    "iostat_r_await_p99_us": iostat["rawait_p99"],
    "iostat_r_await_max_us": iostat["rawait_max"],
    "iostat_aqu_sz": iostat["aqu"],
    "iostat_aqu_p50": iostat["aqu_p50"],
    "iostat_aqu_p90": iostat["aqu_p90"],
    "iostat_aqu_p99": iostat["aqu_p99"],
    "iostat_aqu_max": iostat["aqu_max"],
}

with open(out_file, "w") as f:
    for key, value in summary.items():
        if isinstance(value, float):
            f.write(f"{key}: {value:.2f}\n")
        else:
            f.write(f"{key}: {value}\n")
PY
}

read_summary() {
  local file="$1"
  local key="$2"
  awk -v key="${key}:" '$1 == key { print $2 }' "$file"
}

write_temp_summary() {
  local temp_file="$1"
  local out_file="$2"

  if [[ ! -s "$temp_file" ]]; then
    {
      echo "samples: 0"
      echo "start_c: N/A"
      echo "end_c: N/A"
      echo "min_c: N/A"
      echo "avg_c: N/A"
      echo "max_c: N/A"
      echo "duration_s: N/A"
    } > "$out_file"
    return
  fi

  awk -F, '
    NR > 1 && $3 != "" {
      n++
      temp = $3 + 0
      elapsed = $2 + 0
      if (n == 1) {
        start = temp
        min = temp
        max = temp
      }
      end = temp
      sum += temp
      if (temp < min) min = temp
      if (temp > max) max = temp
      duration = elapsed
    }
    END {
      if (n == 0) {
        print "samples: 0"
        print "start_c: N/A"
        print "end_c: N/A"
        print "min_c: N/A"
        print "avg_c: N/A"
        print "max_c: N/A"
        print "duration_s: N/A"
      } else {
        printf "samples: %d\n", n
        printf "start_c: %.2f\n", start
        printf "end_c: %.2f\n", end
        printf "min_c: %.2f\n", min
        printf "avg_c: %.2f\n", sum / n
        printf "max_c: %.2f\n", max
        printf "duration_s: %.2f\n", duration
      }
    }
  ' "$temp_file" > "$out_file"
}

print_performance_table() {
  printf "DiskANN performance table:\n"
  printf "%6s %11s %15s %15s %16s %15s %16s %15s %15s %15s %15s %15s\n" \
    "L" "Beamwidth" "QPS" "Mean Latency" "99.9 Latency" "Mean IOs" \
    "Mean IO (us)" "CPU (s)" "Cache Hits" "Mean Hops" "Cache Hit Rate" "Recall@10"
  printf "%s\n" "===================================================================================================================================================================================="

  for l_value in ${L_VALUES}; do
    local run_label perf_file
    run_label="${INDEX_VARIANT}_L${l_value}_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}"
    perf_file="${RESULT_DIR}/${run_label}.performance_table.txt"
    require_file "$perf_file"

    awk '$1 ~ /^[0-9]+$/ {
      printf "%6s %11s %15s %15s %16s %15s %16s %15s %15s %15s %15s %15s\n",
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
      exit
    }' "$perf_file"
  done
}

print_latency_table() {
  printf "DiskANN real SSD latency breakdown table:\n"
  printf "%6s %9s %10s %10s %11s %11s %10s %10s %10s %10s %10s %8s %8s %8s %14s %14s %12s %12s\n" \
    "L" "QPS" "MeanLat" "P999Lat" "MeanIO(us)" "MeanHops" \
    "HopP50" "HopP90" "HopP99" "HopP999" "HopMax" \
    "QDAvg" "QDP99" "QDMax" "QryMaxP999" "QryIOSum999" "rAwait(us)" "aqu-sz"
  printf "%s\n" "========================================================================================================================================================================================"

  for l_value in ${L_VALUES}; do
    local run_label summary
    run_label="${INDEX_VARIANT}_L${l_value}_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}"
    summary="${RESULT_DIR}/${run_label}.latency_summary.txt"
    require_file "$summary"

    printf "%6s %9s %10s %10s %11s %11s %10s %10s %10s %10s %10s %8s %8s %8s %14s %14s %12s %12s\n" \
      "$(read_summary "$summary" L)" \
      "$(read_summary "$summary" QPS)" \
      "$(read_summary "$summary" MeanLat)" \
      "$(read_summary "$summary" P999Lat)" \
      "$(read_summary "$summary" MeanIO_us)" \
      "$(read_summary "$summary" MeanHops)" \
      "$(read_summary "$summary" HopIO_p50)" \
      "$(read_summary "$summary" HopIO_p90)" \
      "$(read_summary "$summary" HopIO_p99)" \
      "$(read_summary "$summary" HopIO_p999)" \
      "$(read_summary "$summary" HopIO_max)" \
      "$(read_summary "$summary" QD_avg)" \
      "$(read_summary "$summary" QD_p99)" \
      "$(read_summary "$summary" QD_max)" \
      "$(read_summary "$summary" QueryMaxIO_p999)" \
      "$(read_summary "$summary" QueryIOsum_p999)" \
      "$(read_summary "$summary" iostat_r_await_us)" \
      "$(read_summary "$summary" iostat_aqu_sz)"
  done

  echo
  printf "iostat time-series distribution table:\n"
  printf "%6s %12s %12s %12s %12s %12s %10s %10s %10s %10s %10s\n" \
    "L" "rAwAvg(us)" "rAwP50(us)" "rAwP90(us)" "rAwP99(us)" "rAwMax(us)" \
    "aquAvg" "aquP50" "aquP90" "aquP99" "aquMax"
  printf "%s\n" "========================================================================================================================"

  for l_value in ${L_VALUES}; do
    local run_label summary
    run_label="${INDEX_VARIANT}_L${l_value}_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}"
    summary="${RESULT_DIR}/${run_label}.latency_summary.txt"
    require_file "$summary"

    printf "%6s %12s %12s %12s %12s %12s %10s %10s %10s %10s %10s\n" \
      "$(read_summary "$summary" L)" \
      "$(read_summary "$summary" iostat_r_await_us)" \
      "$(read_summary "$summary" iostat_r_await_p50_us)" \
      "$(read_summary "$summary" iostat_r_await_p90_us)" \
      "$(read_summary "$summary" iostat_r_await_p99_us)" \
      "$(read_summary "$summary" iostat_r_await_max_us)" \
      "$(read_summary "$summary" iostat_aqu_sz)" \
      "$(read_summary "$summary" iostat_aqu_p50)" \
      "$(read_summary "$summary" iostat_aqu_p90)" \
      "$(read_summary "$summary" iostat_aqu_p99)" \
      "$(read_summary "$summary" iostat_aqu_max)"
  done

  echo
  echo "Note: HopP* is DiskANN per-hop synchronous read-batch time. It approximates the slowest read batch in that hop, not individual NVMe command latency."
  echo "Note: rAwait(us)/aqu-sz come from iostat when DEVICE is set. Q->D/D->C/Q->C need blktrace/bpftrace support and are not available in this table yet."
}

print_temperature_table() {
  printf "NVMe temperature table:\n"
  printf "%6s %9s %10s %10s %10s %10s %10s %12s\n" \
    "L" "Samples" "Start(C)" "End(C)" "Min(C)" "Avg(C)" "Max(C)" "Duration(s)"
  printf "%s\n" "========================================================================================"

  for l_value in ${L_VALUES}; do
    local run_label summary
    run_label="${INDEX_VARIANT}_L${l_value}_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}"
    summary="${RESULT_DIR}/${run_label}.nvme_temp_summary.txt"
    require_file "$summary"

    printf "%6s %9s %10s %10s %10s %10s %10s %12s\n" \
      "$l_value" \
      "$(read_summary "$summary" samples)" \
      "$(read_summary "$summary" start_c)" \
      "$(read_summary "$summary" end_c)" \
      "$(read_summary "$summary" min_c)" \
      "$(read_summary "$summary" avg_c)" \
      "$(read_summary "$summary" max_c)" \
      "$(read_summary "$summary" duration_s)"
  done

  echo
  echo "Note: NVMe temperature is sampled from the controller sensor. It is a time-series approximation, not true per-I/O temperature."
}

require_exe "$SEARCH_BIN"
require_file "${INDEX_PREFIX}_disk.index"
require_file "${INDEX_PREFIX}_pq_pivots.bin"
require_file "${INDEX_PREFIX}_pq_compressed.bin"
require_file "$QUERY_FILE"
require_file "$GT_FILE"
mkdir -p "$RESULT_DIR"

for l_value in ${L_VALUES}; do
  run_label="${INDEX_VARIANT}_L${l_value}_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}"
  result_prefix="${RESULT_DIR}/${run_label}"
  log_file="${RESULT_DIR}/${run_label}.log"
  perf_file="${RESULT_DIR}/${run_label}.performance_table.txt"
  trace_csv="${RESULT_DIR}/${run_label}.iteration_trace.csv"
  iostat_file="${RESULT_DIR}/${run_label}.iostat.txt"
  summary_file="${RESULT_DIR}/${run_label}.latency_summary.txt"
  temp_file="${RESULT_DIR}/${run_label}.nvme_temp.csv"
  temp_summary_file="${RESULT_DIR}/${run_label}.nvme_temp_summary.txt"
  iostat_pid=""
  temp_pid=""
  search_status=0

  rm -f "$trace_csv" "$iostat_file" "$summary_file" "$temp_file" "$temp_summary_file"

  search_args=(
    --data_type "$DATA_TYPE"
    --dist_fn "$DIST_FN"
    --index_path_prefix "$INDEX_PREFIX"
    --result_path "$result_prefix"
    --query_file "$QUERY_FILE"
    --gt_file "$GT_FILE"
    -K "$K"
    -W "$W"
    -T "$T"
    --num_nodes_to_cache "$NUM_NODES_TO_CACHE"
    --trace_stats_csv "$trace_csv"
    --trace_sample_rate "$TRACE_SAMPLE_RATE"
    --trace_max_queries "$TRACE_MAX_QUERIES"
    --trace_run_label "$run_label"
    -L "$l_value"
  )

  map_file="${INDEX_PREFIX}_disk.index_block_shuffle_new_to_old.bin"
  if [[ -f "$map_file" ]]; then
    search_args+=(--result_new_to_old_map "$map_file")
  fi
  if [[ "$USE_SECTOR_CANDIDATES" == "1" ]]; then
    search_args+=(--use_sector_candidates)
  fi

  echo
  echo "Running real SSD DiskANN L=${l_value}"
  drop_os_caches
  wash_ssd_cache
  drop_os_caches
  iostat_pid="$(run_iostat "$DEVICE" "$iostat_file" || true)"
  temp_sensor="$(find_nvme_temp_sensor "$DEVICE" || true)"
  temp_pid="$(run_temp_logger "$temp_sensor" "$temp_file" || true)"
  trap 'stop_background "$temp_pid"; stop_background "$iostat_pid"' EXIT
  set +e
  "${SEARCH_BIN}" "${search_args[@]}" | tee "$log_file"
  search_status="${PIPESTATUS[0]}"
  set -e
  stop_background "$temp_pid"
  stop_background "$iostat_pid"
  trap - EXIT
  if [[ "$search_status" -ne 0 ]]; then
    echo "DiskANN search failed for L=${l_value}" >&2
    exit "$search_status"
  fi

  extract_performance_table "$log_file" "$perf_file"
  analyze_trace "$trace_csv" "$perf_file" "$iostat_file" "$summary_file"
  write_temp_summary "$temp_file" "$temp_summary_file"
done

echo
print_performance_table | tee "$PERF_SUMMARY_FILE"
echo
echo "Saved performance table:"
echo "  $PERF_SUMMARY_FILE"

echo
print_latency_table | tee "$SUMMARY_FILE"
echo
print_temperature_table | tee "${RESULT_DIR}/${INDEX_VARIANT}_L_sweep_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}.temperature_summary.txt"
echo
echo "Saved:"
echo "  $SUMMARY_FILE"
