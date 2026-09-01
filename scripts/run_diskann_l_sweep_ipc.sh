#!/usr/bin/env bash
set -euo pipefail

DISKANN_DIR="${DISKANN_DIR:-/home/emmanuel/projects/DiskANN_cpp}"
DISKANN_RUN_SCRIPT="${DISKANN_RUN_SCRIPT:-${DISKANN_DIR}/run_nvmevirt_mqsim_sift1m.sh}"
RESULT_DIR="${RESULT_DIR:-${DISKANN_DIR}/results/nvmevirt_mqsim}"
NVMEV_MOUNT="${NVMEV_MOUNT:-/mnt/nvmevirt}"
INDEX_VARIANT="${INDEX_VARIANT:-block_shuffle}"
L_VALUES="${L_VALUES:-20 40 60 80 100 120}"
W="${W:-16}"
T="${T:-1}"
NUM_NODES_TO_CACHE="${NUM_NODES_TO_CACHE:-0}"
IPC_PROC="${IPC_PROC:-/proc/nvmev/mqsim_ipc}"
SUMMARY_FILE="${SUMMARY_FILE:-${RESULT_DIR}/${INDEX_VARIANT}_L_sweep_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}.ipc_table.txt}"
PERF_SUMMARY_FILE="${PERF_SUMMARY_FILE:-${RESULT_DIR}/${INDEX_VARIANT}_L_sweep_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}.performance_summary.txt}"
IPC_RATIO_PREFIX="${IPC_RATIO_PREFIX:-${RESULT_DIR}/${INDEX_VARIANT}_L_sweep_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}.ipc_ratio}"
IPC_PLOT_DIR="${IPC_PLOT_DIR:-${RESULT_DIR}/ipc_plots}"

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Missing file: $path" >&2
    exit 1
  fi
}

read_counter() {
  local file="$1"
  local key="$2"
  awk -v key="${key}:" '$1 == key { print $2 }' "$file"
}

delta_counter() {
  local before="$1"
  local after="$2"
  local key="$3"
  local b a

  b="$(read_counter "$before" "$key" || echo 0)"
  a="$(read_counter "$after" "$key" || echo 0)"
  echo "$((a - b))"
}

delta_avg_ns() {
  local before="$1"
  local after="$2"
  local count_key="$3"
  local avg_key="$4"
  local before_count after_count before_avg after_avg delta_count delta_total

  before_count="$(read_counter "$before" "$count_key" || echo 0)"
  after_count="$(read_counter "$after" "$count_key" || echo 0)"
  before_avg="$(read_counter "$before" "$avg_key" || echo 0)"
  after_avg="$(read_counter "$after" "$avg_key" || echo 0)"
  delta_count="$((after_count - before_count))"
  if [[ "$delta_count" -le 0 ]]; then
    echo 0
    return
  fi
  delta_total="$((after_count * after_avg - before_count * before_avg))"
  echo "$((delta_total / delta_count))"
}

ns_to_us() {
  local ns="$1"
  awk -v ns="$ns" 'BEGIN { printf "%.2f", ns / 1000.0 }'
}

perf_field() {
  local perf_file="$1"
  local col="$2"
  awk -v col="$col" '$1 ~ /^[0-9]+$/ { print $col; exit }' "$perf_file"
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

print_ipc_table() {
  printf "DiskANN MQSim IPC cost table:\n"
  printf "%6s %10s %10s %12s %12s %12s %12s %12s %10s %10s %10s %10s %10s\n" \
    "L" "QPS" "MeanLat" "MeanIO(us)" "ReqDelta" "ReplyDelta" \
    "RTAvg(us)" "Submit(us)" "LateCnt" "LateAvg" "Fallbacks" "SendErr" "RingFull"
  printf "%s\n" "===================================================================================================================================================="

  for l_value in ${L_VALUES}; do
    local run_label perf_file before_file after_file
    local qps mean_lat mean_io req_delta reply_delta rt_avg_ns submit_avg_ns
    local late_delta late_avg_ns fallbacks_delta send_errors_delta ring_full_delta

    run_label="${INDEX_VARIANT}_L${l_value}_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}"
    perf_file="${RESULT_DIR}/${run_label}.performance_table.txt"
    before_file="${RESULT_DIR}/${run_label}.mqsim_before.txt"
    after_file="${RESULT_DIR}/${run_label}.mqsim_after.txt"

    require_file "$perf_file"
    require_file "$before_file"
    require_file "$after_file"

    qps="$(perf_field "$perf_file" 3)"
    mean_lat="$(perf_field "$perf_file" 4)"
    mean_io="$(perf_field "$perf_file" 7)"
    req_delta="$(delta_counter "$before_file" "$after_file" requests)"
    reply_delta="$(delta_counter "$before_file" "$after_file" replies)"
    rt_avg_ns="$(delta_avg_ns "$before_file" "$after_file" roundtrip_count roundtrip_avg_ns)"
    submit_avg_ns="$(delta_avg_ns "$before_file" "$after_file" submit_cost_count submit_cost_avg_ns)"
    late_delta="$(delta_counter "$before_file" "$after_file" reply_late_count)"
    late_avg_ns="$(delta_avg_ns "$before_file" "$after_file" reply_late_count reply_late_avg_ns)"
    fallbacks_delta="$(delta_counter "$before_file" "$after_file" fallbacks)"
    send_errors_delta="$(delta_counter "$before_file" "$after_file" send_errors)"
    ring_full_delta="$(delta_counter "$before_file" "$after_file" req_ring_full)"

    printf "%6s %10s %10s %12s %12s %12s %12s %12s %10s %10s %10s %10s %10s\n" \
      "$l_value" "$qps" "$mean_lat" "$mean_io" "$req_delta" "$reply_delta" \
      "$(ns_to_us "$rt_avg_ns")" "$(ns_to_us "$submit_avg_ns")" \
      "$late_delta" "$(ns_to_us "$late_avg_ns")" \
      "$fallbacks_delta" "$send_errors_delta" "$ring_full_delta"
  done
}

require_file "$DISKANN_RUN_SCRIPT"

if [[ ! -r "$IPC_PROC" ]]; then
  echo "Missing $IPC_PROC; is nvmev loaded with mqsim_ipc_enable=1?" >&2
  exit 1
fi

if ! awk '$1 == "daemon_connected:" && $2 == "1" { found = 1 } END { exit found ? 0 : 1 }' "$IPC_PROC"; then
  echo "MQSim daemon is not connected." >&2
  cat "$IPC_PROC" >&2
  exit 1
fi

mkdir -p "$RESULT_DIR"

for l_value in ${L_VALUES}; do
  run_label="${INDEX_VARIANT}_L${l_value}_W${W}_T${T}_cache${NUM_NODES_TO_CACHE}"
  echo
  echo "Running DiskANN L=${l_value}"
  NVMEV_MOUNT="$NVMEV_MOUNT" \
  INDEX_VARIANT="$INDEX_VARIANT" \
  L_VALUES="$l_value" \
  W="$W" \
  T="$T" \
  NUM_NODES_TO_CACHE="$NUM_NODES_TO_CACHE" \
  RUN_LABEL="$run_label" \
  RESULT_DIR="$RESULT_DIR" \
    "$DISKANN_RUN_SCRIPT"
done

echo
print_performance_table | tee "$PERF_SUMMARY_FILE"
echo
echo "Saved performance table:"
echo "  $PERF_SUMMARY_FILE"

echo
print_ipc_table | tee "$SUMMARY_FILE"
echo
echo "Saved IPC table:"
echo "  $SUMMARY_FILE"

echo
python3 "$(dirname "$0")/summarize_ipc_l_sweep.py" \
  --result-dir "$RESULT_DIR" \
  --index-variant "$INDEX_VARIANT" \
  --l-values "$L_VALUES" \
  --w "$W" \
  --t "$T" \
  --cache "$NUM_NODES_TO_CACHE" \
  --out-prefix "$IPC_RATIO_PREFIX" \
  --plot-dir "$IPC_PLOT_DIR"
