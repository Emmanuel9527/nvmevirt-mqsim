#!/usr/bin/env bash
set -euo pipefail

# Default target is the block-shuffled SIFT1M disk index on the NVMeVirt mount.
# REFERENCE_FILE points to the original copy on the real SSD.  Each read from
# NVMeVirt is compared against the same byte range in REFERENCE_FILE.
# Override READ_FILE/REFERENCE_FILE/OFFSETS/BS from the shell to test another
# file or range.
READ_FILE="${READ_FILE:-/mnt/nvmevirt/sift1m_diskann_index/sift1m_l2_R64_L100_pq0_block_shuffle_disk.index}"
REFERENCE_FILE="${REFERENCE_FILE:-/home/emmanuel/projects/data/sift1m_diskann_indexes/sift1m_l2_R64_L100_pq0_block_shuffle_disk.index}"
IPC_PROC="${IPC_PROC:-/proc/nvmev/mqsim_ipc}"
BS="${BS:-4096}"
OFFSETS="${OFFSETS:-0 4096 8192}"
OUT_DIR="${OUT_DIR:-/tmp/nvmevirt_three_reads}"

# Fail early if a required userspace tool is unavailable.
require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing command: ${cmd}" >&2
    exit 1
  fi
}

# Read one numeric field from /proc/nvmev/mqsim_ipc snapshots.
read_counter() {
  local file="$1"
  local key="$2"
  awk -v key="${key}:" '$1 == key { print $2 }' "${file}" 2>/dev/null || true
}

# /proc files may be read-only, and cp can preserve that mode on the snapshot.
# Remove the old snapshot first so repeated runs can refresh the file cleanly.
save_ipc_snapshot() {
  local out_file="$1"

  rm -f "${out_file}"
  cat "${IPC_PROC}" > "${out_file}"
}

# Print before/after counter deltas to prove whether the reads reached MQSim IPC.
print_counter_delta() {
  local before="$1"
  local after="$2"
  local key="$3"
  local b a

  b="$(read_counter "${before}" "${key}")"
  a="$(read_counter "${after}" "${key}")"
  if [[ -n "${b}" && -n "${a}" ]]; then
    printf '  %-16s %s -> %s  delta=%s\n' "${key}" "${b}" "${a}" "$((a - b))"
  fi
}

# Use filefrag to translate the file logical offset into the current block
# device LBA range.  This shows which host-visible logical blocks the read
# should generate after the filesystem extent mapping.
print_extent_for_offset() {
  local file="$1"
  local offset="$2"
  local block_index

  block_index=$((offset / 512))
  filefrag -b512 -v "${file}" 2>/dev/null |
    awk -v blk="${block_index}" '
      $1 ~ /^[0-9]+:/ {
        logical = $2
        physical = $4
        gsub(":", "", logical)
        gsub(":", "", physical)
        split(logical, lrange, /\.\./)
        split(physical, prange, /\.\./)
        if (blk >= lrange[1] && blk <= lrange[2]) {
          physical_block = prange[1] + (blk - lrange[1])
          printf "  filesystem extent: file_lba512=%s..%s device_lba512=%s..%s read_device_lba512=%s\n",
                 lrange[1], lrange[2], prange[1], prange[2], physical_block
          found = 1
          exit
        }
      }
      END {
        if (!found)
          print "  filesystem extent: not found in filefrag output"
      }
    '
}

diagnose_missing_read_file() {
  echo "Missing READ_FILE: ${READ_FILE}" >&2
  echo >&2
  echo "NVMeVirt mount status:" >&2
  if [[ -d /mnt/nvmevirt ]]; then
    findmnt -T /mnt/nvmevirt -o TARGET,SOURCE,FSTYPE,OPTIONS -n >&2 || true
  else
    echo "  /mnt/nvmevirt does not exist" >&2
  fi
  echo >&2
  echo "Block devices currently visible:" >&2
  lsblk -o NAME,MODEL,SIZE,FSTYPE,MOUNTPOINTS >&2 || true
  echo >&2
  echo "Index candidates on /mnt/nvmevirt:" >&2
  find /mnt/nvmevirt -maxdepth 4 -type f -name '*disk.index' -print 2>/dev/null | sort >&2 || true
  echo >&2
  echo "Index candidates in /home/emmanuel/projects/data:" >&2
  find /home/emmanuel/projects/data -maxdepth 4 -type f -name '*disk.index' -print 2>/dev/null | sort >&2 || true
  echo >&2
  echo "Override it with: READ_FILE=/path/to/file $0" >&2
}

# Tools used by this smoke test.
require_cmd dd
require_cmd filefrag
require_cmd hexdump
require_cmd stat
require_cmd awk
require_cmd date
require_cmd lsblk
require_cmd cmp
require_cmd cksum

if [[ ! -f "${READ_FILE}" ]]; then
  diagnose_missing_read_file
  exit 1
fi

if [[ ! -f "${REFERENCE_FILE}" ]]; then
  echo "Missing REFERENCE_FILE: ${REFERENCE_FILE}" >&2
  echo "Override it with: REFERENCE_FILE=/path/to/original/file $0" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

# Save counter snapshots around the three direct reads.
before_counters="${OUT_DIR}/mqsim_before.txt"
after_counters="${OUT_DIR}/mqsim_after.txt"

echo "Three-read NVMeVirt/MQSim smoke test"
echo "  file=${READ_FILE}"
echo "  reference_file=${REFERENCE_FILE}"
echo "  read_size=${BS} bytes"
echo "  offsets=${OFFSETS}"
echo "  output_dir=${OUT_DIR}"
echo

echo "System / file information:"
echo "  time: $(date --iso-8601=seconds)"
echo "  kernel: $(uname -r)"
echo "  file_size_bytes: $(stat -c '%s' "${READ_FILE}")"
echo "  mount: $(findmnt -T "${READ_FILE}" -o TARGET,SOURCE,FSTYPE,OPTIONS -n 2>/dev/null || echo unknown)"
echo "  block_device: $(findmnt -T "${READ_FILE}" -o SOURCE -n 2>/dev/null || echo unknown)"
echo "  reference_file_size_bytes: $(stat -c '%s' "${REFERENCE_FILE}")"
echo

# If MQSim IPC is active, capture its initial state.  The script can still read
# data without this proc file, but then it cannot verify MQSim counter changes.
if [[ -r "${IPC_PROC}" ]]; then
  save_ipc_snapshot "${before_counters}"
  echo "MQSim IPC counters before:"
  cat "${before_counters}"
  echo
else
  echo "MQSim IPC counters before: ${IPC_PROC} is not readable"
  echo
fi

# Issue exactly three direct 4KiB reads by default.  iflag=direct bypasses the
# page cache so the reads go through the block/NVMeVirt path instead of being
# served from Linux file cache.
i=0
for offset in ${OFFSETS}; do
  i=$((i + 1))
  out_file="${OUT_DIR}/read_${i}_offset_${offset}.bin"
  ref_out_file="${OUT_DIR}/reference_${i}_offset_${offset}.bin"
  timing_file="${OUT_DIR}/read_${i}_timing.txt"

  echo "Read ${i}:"
  echo "  file_offset_bytes=${offset}"
  print_extent_for_offset "${READ_FILE}" "${offset}"

  # dd skip is expressed in units of BS, so the offsets should be BS-aligned.
  /usr/bin/time -f '  elapsed_seconds=%e user_seconds=%U sys_seconds=%S' \
    -o "${timing_file}" \
    dd if="${READ_FILE}" of="${out_file}" bs="${BS}" skip="$((offset / BS))" count=1 iflag=direct status=none

  # Read the same byte range from the original file on the real SSD.  This is
  # the correctness reference for the NVMeVirt backing-store bytes.
  dd if="${REFERENCE_FILE}" of="${ref_out_file}" bs="${BS}" skip="$((offset / BS))" count=1 iflag=direct status=none

  # Dump a small data fingerprint so we can confirm the read returned real bytes.
  echo "  bytes_read=$(stat -c '%s' "${out_file}")"
  echo "  nvmevirt_checksum=$(cksum "${out_file}" | awk '{print $1 ":" $2}')"
  echo "  reference_checksum=$(cksum "${ref_out_file}" | awk '{print $1 ":" $2}')"
  if cmp -s "${out_file}" "${ref_out_file}"; then
    echo "  compare_with_reference=match"
  else
    echo "  compare_with_reference=MISMATCH"
    cmp -l "${out_file}" "${ref_out_file}" | sed -n '1,8p' | sed 's/^/    first_different_byte: /'
  fi
  echo "  first_64_bytes:"
  hexdump -C -n 64 "${out_file}" | sed 's/^/    /'
  cat "${timing_file}"
  echo
done

sync

# Compare MQSim IPC counters.  For three single-block reads, requests/replies
# should usually increase by three if the daemon is connected and no fallback
# path was used.
if [[ -r "${IPC_PROC}" ]]; then
  save_ipc_snapshot "${after_counters}"
  echo "MQSim IPC counter deltas:"
  print_counter_delta "${before_counters}" "${after_counters}" requests
  print_counter_delta "${before_counters}" "${after_counters}" replies
  print_counter_delta "${before_counters}" "${after_counters}" fallbacks
  print_counter_delta "${before_counters}" "${after_counters}" send_errors
  print_counter_delta "${before_counters}" "${after_counters}" req_ring_full
  print_counter_delta "${before_counters}" "${after_counters}" late_replies
  echo "  pending          $(read_counter "${after_counters}" pending)"
  echo "  max_pending      $(read_counter "${after_counters}" max_pending)"
fi
