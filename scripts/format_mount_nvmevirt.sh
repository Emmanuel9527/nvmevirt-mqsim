#!/usr/bin/env bash
set -euo pipefail

DEV="${1:-}"
MOUNT_DIR="${2:-/mnt/nvmevirt}"
EXPECTED_MODEL="${EXPECTED_MODEL:-CSL_Virt_MN_01}"
FS_TYPE="${FS_TYPE:-ext4}"
CONFIRM_FORMAT="${CONFIRM_FORMAT:-0}"

if [[ -z "$DEV" ]]; then
  echo "Usage: CONFIRM_FORMAT=1 $0 /dev/nvmeXnY [/mnt/nvmevirt]" >&2
  echo >&2
  echo "Environment:" >&2
  echo "  EXPECTED_MODEL  expected lsblk MODEL, default: $EXPECTED_MODEL" >&2
  echo "  FS_TYPE         filesystem type, default: $FS_TYPE" >&2
  echo "  CONFIRM_FORMAT  must be 1 to run mkfs" >&2
  exit 1
fi

if [[ "$CONFIRM_FORMAT" != "1" ]]; then
  echo "Refusing to format without CONFIRM_FORMAT=1" >&2
  echo "Example: CONFIRM_FORMAT=1 $0 $DEV $MOUNT_DIR" >&2
  exit 1
fi

if [[ ! -b "$DEV" ]]; then
  echo "Not a block device: $DEV" >&2
  exit 1
fi

if [[ "$DEV" != /dev/nvme*n* ]]; then
  echo "Refusing to format a non-NVMe namespace path: $DEV" >&2
  exit 1
fi

if findmnt -S "$DEV" >/dev/null; then
  echo "Device is already mounted:" >&2
  findmnt -S "$DEV" >&2
  exit 1
fi

model="$(lsblk -dn -o MODEL "$DEV" | sed 's/[[:space:]]*$//')"
if [[ -n "$EXPECTED_MODEL" && "$model" != "$EXPECTED_MODEL" ]]; then
  echo "Device model mismatch for $DEV" >&2
  echo "  expected: $EXPECTED_MODEL" >&2
  echo "  actual:   $model" >&2
  exit 1
fi

echo "Formatting NVMeVirt namespace:"
lsblk -o NAME,PATH,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS "$DEV"

case "$FS_TYPE" in
  ext4)
    sudo mkfs.ext4 -F "$DEV"
    ;;
  xfs)
    sudo mkfs.xfs -f "$DEV"
    ;;
  *)
    echo "Unsupported FS_TYPE: $FS_TYPE" >&2
    exit 1
    ;;
esac

sudo mkdir -p "$MOUNT_DIR"
sudo mount "$DEV" "$MOUNT_DIR"
sudo chown "$USER":"$USER" "$MOUNT_DIR"

echo
echo "Mounted:"
findmnt -T "$MOUNT_DIR" -o TARGET,SOURCE,FSTYPE,OPTIONS
