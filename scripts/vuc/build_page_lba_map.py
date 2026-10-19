#!/usr/bin/env python3
"""Convert a page-aligned file's FIEMAP extents to page-start NVMe LBAs."""

import argparse
import re
import struct
import subprocess
from pathlib import Path


SECTORS_PER_PAGE = 8
EXTENT_RE = re.compile(
    r"^\s*\d+:\s+(\d+)\.\.\s+(\d+):\s+(\d+)\.\.\s+(\d+):\s+(\d+):"
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--partition-start-slba", type=int, default=0,
                   help="Add this if filefrag reports LBAs relative to a partition")
    args = p.parse_args()
    file_bytes = args.file.stat().st_size
    if file_bytes == 0 or file_bytes % 4096:
        raise SystemExit("input file must be nonempty and 4 KiB aligned")
    pages = [None] * (file_bytes // 4096)
    result = subprocess.run(["filefrag", "-b512", "-v", str(args.file)],
                            check=True, text=True, capture_output=True)
    for line in result.stdout.splitlines():
        m = EXTENT_RE.match(line)
        if not m:
            continue
        logical_start, logical_end, physical_start, physical_end, length = map(int, m.groups())
        if logical_end - logical_start + 1 != length or physical_end - physical_start + 1 != length:
            raise SystemExit(f"extent range length mismatch: {line}")
        if (logical_start % SECTORS_PER_PAGE or physical_start % SECTORS_PER_PAGE or
                length % SECTORS_PER_PAGE):
            raise SystemExit(f"extent is not 4 KiB aligned; cannot model it as page reads: {line}")
        if logical_end >= file_bytes // 512:
            raise SystemExit(f"extent exceeds file size: {line}")
        for page_offset in range(length // SECTORS_PER_PAGE):
            pages[logical_start // SECTORS_PER_PAGE + page_offset] = (
                physical_start + page_offset * SECTORS_PER_PAGE + args.partition_start_slba
            )
    if any(x is None for x in pages):
        raise SystemExit("FIEMAP did not cover every file sector (sparse/unknown extent?)")
    with args.output.open("wb") as out:
        out.write(struct.pack("<II", len(pages), 1))
        out.write(struct.pack("<" + "Q" * len(pages), *pages))
    print(f"Wrote {len(pages)} page-start LBAs to {args.output}")


if __name__ == "__main__":
    main()
