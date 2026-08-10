#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 FILE [FILE ...]" >&2
  exit 1
fi

echo "# file,file_offset_bytes,slba,nlb"

for file in "$@"; do
  filefrag -b512 -v "$file" | awk -v file="$file" '
    /^[[:space:]]*[0-9]+:/ {
      logical_start = $2
      physical_start = $4
      extent_len = $6
      gsub(/\.\..*/, "", logical_start)
      gsub(/\.\..*/, "", physical_start)
      gsub(/:/, "", physical_start)
      gsub(/:/, "", extent_len)
      if (physical_start ~ /^[0-9]+$/ && extent_len ~ /^[0-9]+$/) {
        printf "%s,%.0f,%.0f,%.0f\n", file, logical_start * 512, physical_start, extent_len
      }
    }
  '
done
