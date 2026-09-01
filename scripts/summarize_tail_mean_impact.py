#!/usr/bin/env python3
import argparse
import csv
import math
import pathlib
import statistics


def pct(values, q):
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = int(math.ceil(q * len(sorted_values))) - 1
    idx = max(0, min(idx, len(sorted_values) - 1))
    return sorted_values[idx]


def mean(values):
    return statistics.fmean(values) if values else 0.0


def read_perf_meanio(path):
    if not path.exists():
        return 0.0
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if parts and parts[0].isdigit():
            return float(parts[6])
    return 0.0


def summarize_run(trace_csv, perf_file):
    per_query_io = {}
    hop_io = []
    issued_reads = 0

    with trace_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                qid = int(row["query_id"])
                io_us = float(row["io_us"])
                issued = int(row["issued_reads"])
            except (KeyError, ValueError):
                continue
            per_query_io[qid] = per_query_io.get(qid, 0.0) + io_us
            if io_us > 0:
                hop_io.append(io_us)
            issued_reads += max(0, issued)

    query_values = list(per_query_io.values())
    query_count = len(query_values)
    hop_count = len(hop_io)
    top001_count = max(1, math.ceil(query_count * 0.001)) if query_count else 0
    top01_count = max(1, math.ceil(query_count * 0.01)) if query_count else 0
    top001_values = sorted(query_values, reverse=True)[:top001_count]
    top01_values = sorted(query_values, reverse=True)[:top01_count]
    total_io = sum(query_values)
    mean_io = mean(query_values)
    perf_meanio = read_perf_meanio(perf_file)

    without_top001 = mean(sorted(query_values)[: query_count - top001_count]) if query_count > top001_count else 0.0
    without_top01 = mean(sorted(query_values)[: query_count - top01_count]) if query_count > top01_count else 0.0

    return {
        "L": int(trace_csv.name.split("_L", 1)[1].split("_", 1)[0]),
        "QueryN": query_count,
        "HopN": hop_count,
        "IssuedReads": issued_reads,
        "MeanIO_trace_us": mean_io,
        "MeanIO_perf_us": perf_meanio,
        "QueryIO_p99_us": pct(query_values, 0.99),
        "QueryIO_p999_us": pct(query_values, 0.999),
        "QueryIO_max_us": max(query_values) if query_values else 0.0,
        "Top0.1N": top001_count,
        "Top0.1Avg_us": mean(top001_values),
        "Top0.1Contribution_pct": 100.0 * sum(top001_values) / total_io if total_io else 0.0,
        "MeanWithoutTop0.1_us": without_top001,
        "MeanDropTop0.1_us": mean_io - without_top001,
        "Top1N": top01_count,
        "Top1Contribution_pct": 100.0 * sum(top01_values) / total_io if total_io else 0.0,
        "MeanWithoutTop1_us": without_top01,
        "MeanDropTop1_us": mean_io - without_top01,
        "HopIO_p999_us": pct(hop_io, 0.999),
        "HopIO_max_us": max(hop_io) if hop_io else 0.0,
    }


def print_table(rows):
    print("DiskANN tail contribution to MeanIO:")
    print(
        f"{'L':>6} {'QueryN':>8} {'Top0.1N':>8} {'MeanIO':>10} {'QIOp999':>10} "
        f"{'QIOmax':>10} {'Top0.1Avg':>11} {'Top0.1%':>9} {'DropMean':>10} "
        f"{'Top1%':>8} {'HopN':>8}"
    )
    print("=" * 122)
    for row in rows:
        print(
            f"{row['L']:6d} {row['QueryN']:8d} {row['Top0.1N']:8d} "
            f"{row['MeanIO_trace_us']:10.2f} {row['QueryIO_p999_us']:10.2f} "
            f"{row['QueryIO_max_us']:10.2f} {row['Top0.1Avg_us']:11.2f} "
            f"{row['Top0.1Contribution_pct']:9.3f} {row['MeanDropTop0.1_us']:10.2f} "
            f"{row['Top1Contribution_pct']:8.3f} {row['HopN']:8d}"
        )
    print()
    print("Top0.1% means the slowest 0.1% queries. With 10,000 queries, the denominator is 10,000 and Top0.1N is 10.")
    print("DropMean is how much MeanIO decreases after removing the slowest 0.1% queries.")


def main():
    parser = argparse.ArgumentParser(description="Estimate how much tail queries contribute to DiskANN MeanIO.")
    parser.add_argument("--result-dir", type=pathlib.Path, default=pathlib.Path("/home/emmanuel/projects/DiskANN_cpp/results/real_ssd_latency"))
    parser.add_argument("--index-variant", default="block_shuffle")
    parser.add_argument("--l-values", default="20 40 60 80 100 120")
    parser.add_argument("--w", default="16")
    parser.add_argument("--t", default="1")
    parser.add_argument("--cache", default="0")
    parser.add_argument("--out-csv", type=pathlib.Path)
    args = parser.parse_args()

    rows = []
    for l_value in args.l_values.split():
        run_label = f"{args.index_variant}_L{l_value}_W{args.w}_T{args.t}_cache{args.cache}"
        trace_csv = args.result_dir / f"{run_label}.iteration_trace.csv"
        perf_file = args.result_dir / f"{run_label}.performance_table.txt"
        if not trace_csv.exists():
            raise FileNotFoundError(trace_csv)
        rows.append(summarize_run(trace_csv, perf_file))

    rows.sort(key=lambda row: row["L"])
    print_table(rows)

    out_csv = args.out_csv or (pathlib.Path("plots") / f"{args.index_variant}_L_sweep_W{args.w}_T{args.t}_cache{args.cache}.tail_mean_impact.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {out_csv}")


if __name__ == "__main__":
    main()
