#!/usr/bin/env bash
set -euo pipefail

WASH_FILE="${1:-/home/emmanuel/projects/data/cache_wash_64g.bin}"
WASH_SIZE="${WASH_SIZE:-64G}"
CONFIRM_CREATE="${CONFIRM_CREATE:-0}"

if [[ "$CONFIRM_CREATE" != "1" ]]; then
  echo "Refusing to create/write the cache wash file without CONFIRM_CREATE=1" >&2
  echo "Example: CONFIRM_CREATE=1 $0 $WASH_FILE" >&2
  exit 1
fi

if ! command -v fio >/dev/null 2>&1; then
  echo "fio is not installed or not in PATH." >&2
  exit 1
fi

mkdir -p "$(dirname "$WASH_FILE")"

if [[ -e "$WASH_FILE" ]]; then
  echo "Refusing to overwrite existing file: $WASH_FILE" >&2
  echo "Remove it manually first if you want to recreate it." >&2
  exit 1
fi

echo "Creating cache wash file:"
echo "  file=$WASH_FILE"
echo "  size=$WASH_SIZE"

fio \
  --name=create-cache-wash-file \
  --filename="$WASH_FILE" \
  --rw=write \
  --bs=1M \
  --size="$WASH_SIZE" \
  --ioengine=libaio \
  --iodepth=16 \
  --direct=1 \
  --numjobs=1 \
  --end_fsync=1 \
  --group_reporting

sync
ls -lh "$WASH_FILE"
