#!/usr/bin/env python3
"""Summarize within-iteration sector reuse by normalized search progress.

Each query's iterations are assigned to five lifecycle bins by the DiskANN
trace writer (0-20%, ..., 80-100% of that query's iterations). A batch is one
query/iteration, and sector reuse is measured among node reads in that batch.
"""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


KEY = ("run_label", "L", "beamwidth", "query_id", "iteration")


def read_csv(path):
    with open(path, newline="") as f:
        yield from csv.DictReader(f)


def ratio(a, b):
    return a / b if b else 0.0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", required=True)
    p.add_argument("--access_csv", required=True)
    p.add_argument("--iteration_csv", required=True)
    p.add_argument("--out_csv", required=True)
    args = p.parse_args()

    # The iteration trace supplies the normalized lifecycle bin for each batch.
    bins = {}
    for row in read_csv(args.iteration_csv):
        key = tuple(row[k] for k in KEY)
        bins[key] = int(row["lifecycle_bin"])

    # Count exact sector-start IDs for each query/iteration batch.
    sectors_by_batch = defaultdict(Counter)
    for row in read_csv(args.access_csv):
        key = tuple(row[k] for k in KEY)
        sectors_by_batch[key][row["sector_id"]] += 1

    # Aggregate batch-level counts, retaining zero-read iterations from stats.
    totals = defaultdict(lambda: Counter())
    for key, lifecycle_bin in bins.items():
        counts = sectors_by_batch.get(key, Counter())
        n = sum(counts.values())
        u = len(counts)
        shared_reads = sum(count for count in counts.values() if count >= 2)
        group = (key[1], key[2], lifecycle_bin)
        acc = totals[group]
        acc["batches"] += 1
        acc["shared_batches"] += int(any(count >= 2 for count in counts.values()))
        acc["reads"] += n
        acc["unique_sectors"] += u
        acc["shared_reads"] += shared_reads
        acc["duplicate_reads"] += n - u

    fields = [
        "dataset", "L", "W", "lifecycle_bin", "progress_range",
        "batches", "node_reads_N", "unique_sector_starts_U",
        "batches_with_shared_sector_pct", "node_reads_in_shared_sectors_pct",
        "duplicate_sector_request_ratio_pct",
    ]
    out_path = Path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for (L, W, lifecycle_bin), acc in sorted(totals.items(), key=lambda x: (int(x[0][0]), int(x[0][1]), x[0][2])):
            lo = (lifecycle_bin - 1) * 20
            hi = lifecycle_bin * 20
            writer.writerow({
                "dataset": args.dataset,
                "L": L,
                "W": W,
                "lifecycle_bin": lifecycle_bin,
                "progress_range": f"{lo}-{hi}%",
                "batches": acc["batches"],
                "node_reads_N": acc["reads"],
                "unique_sector_starts_U": acc["unique_sectors"],
                "batches_with_shared_sector_pct": 100 * ratio(acc["shared_batches"], acc["batches"]),
                "node_reads_in_shared_sectors_pct": 100 * ratio(acc["shared_reads"], acc["reads"]),
                "duplicate_sector_request_ratio_pct": 100 * ratio(acc["duplicate_reads"], acc["reads"]),
            })
    print(f"Wrote lifecycle-binned sector reuse to {out_path}")


if __name__ == "__main__":
    main()
