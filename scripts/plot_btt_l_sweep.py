#!/usr/bin/env python3
import argparse
import glob
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_numeric_values(pattern):
    values = []
    for filename in sorted(glob.glob(pattern)):
        with open(filename, "r", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                nums = []
                for token in line.replace(",", " ").split():
                    try:
                        nums.append(float(token))
                    except ValueError:
                        pass
                if nums:
                    values.append(nums[-1])
    if values and max(values) < 10.0:
        values = [v * 1_000_000.0 for v in values]
    return values


def percentile(values, q):
    if not values:
        return 0.0
    arr = np.sort(np.asarray(values, dtype=float))
    idx = int(math.ceil(q * len(arr))) - 1
    idx = max(0, min(idx, len(arr) - 1))
    return float(arr[idx])


def plot_metric_cdf(metric, values_by_l, output_dir):
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    for l_value, values in values_by_l.items():
        if not values:
            continue
        arr = np.sort(np.asarray(values, dtype=float))
        y = np.arange(1, len(arr) + 1) / len(arr)
        ax.plot(arr, y, label=f"L={l_value} n={len(arr)}")

    ax.set_title(f"{metric.upper()} latency CDF by L")
    ax.set_xlabel("Latency (us)")
    ax.set_ylabel("CDF")
    ax.set_xscale("log")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / f"{metric.lower()}_cdf_by_l.png")
    plt.close(fig)


def plot_metric_percentiles(metric, values_by_l, output_dir):
    labels = ["p50", "p90", "p99", "p999", "max"]
    quantiles = [0.50, 0.90, 0.99, 0.999, 1.0]
    l_values = list(values_by_l.keys())
    x = np.arange(len(l_values))
    width = 0.15

    fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
    for i, (label, q) in enumerate(zip(labels, quantiles)):
        heights = []
        for l_value in l_values:
            values = values_by_l[l_value]
            heights.append(max(values) if q == 1.0 and values else percentile(values, q))
        ax.bar(x + (i - 2) * width, heights, width, label=label)

    ax.set_title(f"{metric.upper()} latency percentiles by L")
    ax.set_xlabel("L")
    ax.set_ylabel("Latency (us)")
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in l_values])
    ax.set_yscale("log")
    ax.grid(True, axis="y", which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / f"{metric.lower()}_percentiles_by_l.png")
    plt.close(fig)


def write_summary_csv(metric_values, output_dir):
    out = output_dir / "btt_l_sweep_latency_summary.csv"
    with open(out, "w") as f:
        f.write("metric,L,count,avg_us,p50_us,p90_us,p99_us,p999_us,max_us\n")
        for metric, values_by_l in metric_values.items():
            for l_value, values in values_by_l.items():
                count = len(values)
                avg = float(np.mean(values)) if values else 0.0
                p50 = percentile(values, 0.50)
                p90 = percentile(values, 0.90)
                p99 = percentile(values, 0.99)
                p999 = percentile(values, 0.999)
                max_value = max(values) if values else 0.0
                f.write(
                    f"{metric},{l_value},{count},{avg:.6f},{p50:.6f},{p90:.6f},"
                    f"{p99:.6f},{p999:.6f},{max_value:.6f}\n"
                )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-dir", required=True)
    parser.add_argument("--index-variant", default="block_shuffle")
    parser.add_argument("--l-values", required=True)
    parser.add_argument("--w", default="16")
    parser.add_argument("--t", default="1")
    parser.add_argument("--cache", default="0")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    trace_dir = Path(args.trace_dir)
    output_dir = Path(args.output_dir) if args.output_dir else trace_dir / "l_sweep_plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    l_values = args.l_values.split()
    metric_values = {"q2d": {}, "d2c": {}, "q2c": {}}
    for l_value in l_values:
        run_label = f"{args.index_variant}_L{l_value}_W{args.w}_T{args.t}_cache{args.cache}"
        prefix = trace_dir / f"{run_label}.btt_data"
        metric_values["q2d"][l_value] = read_numeric_values(f"{prefix}.q2d*")
        metric_values["d2c"][l_value] = read_numeric_values(f"{prefix}.d2c*")
        metric_values["q2c"][l_value] = read_numeric_values(f"{prefix}.q2c*")

    for metric, values_by_l in metric_values.items():
        plot_metric_cdf(metric, values_by_l, output_dir)
        plot_metric_percentiles(metric, values_by_l, output_dir)

    summary = write_summary_csv(metric_values, output_dir)
    print(summary)
    for path in sorted(output_dir.glob("*.png")):
        print(path)


if __name__ == "__main__":
    main()
