#!/usr/bin/env bash
set -euo pipefail

DEV="${1:-}"
RUNTIME="${RUNTIME:-10}"
BS="${BS:-4k}"
IODEPTH="${IODEPTH:-1}"

if [[ -z "$DEV" ]]; then
  echo "Usage: $0 /dev/nvmeXnY"
  echo
  echo "This script only runs a direct randread fio test. It does not format,"
  echo "mount, or write to the selected device."
  exit 1
fi

if [[ ! -b "$DEV" ]]; then
  echo "Not a block device: $DEV" >&2
  exit 1
fi

if [[ "$DEV" != /dev/nvme*n* ]]; then
  echo "Refusing to test a non-NVMe namespace path: $DEV" >&2
  exit 1
fi

if ! command -v fio >/dev/null 2>&1; then
  echo "fio is not installed or not in PATH." >&2
  exit 1
fi

echo "Selected device:"
lsblk -o NAME,PATH,SIZE,MODEL,SERIAL,MOUNTPOINTS "$DEV"

echo
echo "NVMeVirt kernel messages:"
dmesg | grep -i "NVMeVirt" | tail -n 20 || true

echo
if [[ -r /proc/nvmev/mqsim_ipc ]]; then
  echo "/proc/nvmev/mqsim_ipc:"
  cat /proc/nvmev/mqsim_ipc
else
  echo "Warning: /proc/nvmev/mqsim_ipc is not readable. Is nvmev loaded?"
fi

echo
echo "About to run a read-only fio test:"
echo "  device:  $DEV"
echo "  bs:      $BS"
echo "  iodepth: $IODEPTH"
echo "  runtime: ${RUNTIME}s"
echo
read -r -p "Type READONLY to continue: " answer
if [[ "$answer" != "READONLY" ]]; then
  echo "Aborted."
  exit 1
fi

sudo fio \
  --name=nvmevirt-safe-randread \
  --filename="$DEV" \
  --rw=randread \
  --bs="$BS" \
  --iodepth="$IODEPTH" \
  --ioengine=libaio \
  --direct=1 \
  --numjobs=1 \
  --runtime="$RUNTIME" \
  --time_based=1

echo
if [[ -r /proc/nvmev/mqsim_ipc ]]; then
  echo "/proc/nvmev/mqsim_ipc after test:"
  cat /proc/nvmev/mqsim_ipc
fi
