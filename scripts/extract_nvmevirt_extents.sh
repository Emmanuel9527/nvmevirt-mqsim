#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 FILE_OR_DIR [FILE_OR_DIR ...]" >&2
  exit 1
fi

echo "# file,file_offset_bytes,slba,nlb"

files=()
for path in "$@"; do
  if [[ -d "$path" ]]; then
    while IFS= read -r file; do
      files+=("$file")
    done < <(find "$path" -maxdepth 1 -type f | sort)
  else
    files+=("$path")
  fi
done

for file in "${files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Skipping non-file path: $file" >&2
    continue
  fi

  filefrag -b512 -v "$file" | awk -v file="$file" '
    /^[[:space:]]*[0-9]+:/ {
      logical_start = $2 $3
      physical_start = $4 $5
      extent_len = $6
      gsub(/\.\..*/, "", logical_start)
      gsub(/\.\..*/, "", physical_start)
      gsub(/:/, "", logical_start)
      gsub(/:/, "", physical_start)
      gsub(/:/, "", extent_len)
      if (physical_start ~ /^[0-9]+$/ && extent_len ~ /^[0-9]+$/) {
        printf "%s,%.0f,%.0f,%.0f\n", file, logical_start * 512, physical_start, extent_len
      }
    }
  '
done
