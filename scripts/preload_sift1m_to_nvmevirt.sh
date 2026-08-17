#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="${SRC_DIR:-/home/emmanuel/projects/data/sift1m_diskann_indexes}"
MOUNT_DIR="${1:-}"
PREFIX="${PREFIX:-sift1m_l2_R64_L100_pq0_default}"
DEST_SUBDIR="${DEST_SUBDIR:-sift1m_diskann_index}"
DROP_CACHES="${DROP_CACHES:-0}"

if [[ -z "$MOUNT_DIR" ]]; then
  echo "Usage: $0 /mnt/nvmevirt"
  echo
  echo "Environment:"
  echo "  SRC_DIR      source index directory, default: $SRC_DIR"
  echo "  PREFIX       DiskANN index prefix, default: $PREFIX"
  echo "  DEST_SUBDIR  directory under mount point, default: $DEST_SUBDIR"
  echo "  DROP_CACHES  set to 1 to run sync + drop_caches after copy"
  exit 1
fi

if [[ ! -d "$MOUNT_DIR" ]]; then
  echo "Mount directory does not exist: $MOUNT_DIR" >&2
  exit 1
fi

if ! mountpoint -q "$MOUNT_DIR"; then
  echo "Not a mount point: $MOUNT_DIR" >&2
  echo "Mount the NVMeVirt namespace first, then rerun this script." >&2
  exit 1
fi

required_files=(
  "${PREFIX}_disk.index"
  "${PREFIX}_pq_compressed.bin"
  "${PREFIX}_pq_pivots.bin"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$SRC_DIR/$file" ]]; then
    echo "Missing source file: $SRC_DIR/$file" >&2
    exit 1
  fi
done

mkdir -p "$MOUNT_DIR/$DEST_SUBDIR"

for file in "${required_files[@]}"; do
  echo "Copying $file ..."
  install -m 0644 "$SRC_DIR/$file" "$MOUNT_DIR/$DEST_SUBDIR/$file"
done

sync

echo "Preloaded files:"
du -h "$MOUNT_DIR/$DEST_SUBDIR"/*

if [[ "$DROP_CACHES" == "1" ]]; then
  if [[ "$(id -u)" != "0" ]]; then
    echo "DROP_CACHES=1 requires root; skipping drop_caches." >&2
  else
    sync
    echo 3 > /proc/sys/vm/drop_caches
    echo "Dropped Linux page cache."
  fi
fi

echo "Done. Point DiskANN to: $MOUNT_DIR/$DEST_SUBDIR"
