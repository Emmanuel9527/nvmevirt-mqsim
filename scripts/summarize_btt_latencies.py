#!/usr/bin/env python3
import argparse
import glob
import math
import os
from pathlib import Path

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    HAVE_MATPLOTLIB = True
except Exception:
    HAVE_MATPLOTLIB = False


def read_numeric_values(pattern):
    values = []
    files = sorted(glob.glob(pattern))
    for filename in files:
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
    return files, values


def to_us(values):
    if not values:
        return []
    max_value = max(values)
    # btt latency files are normally seconds. If a future btt emits already
    # scaled values, avoid multiplying very large numbers into nonsense.
    if max_value < 10.0:
        return [v * 1_000_000.0 for v in values]
    return values


def percentile(sorted_values, q):
    if not sorted_values:
        return 0.0
    idx = int(math.ceil(q * len(sorted_values))) - 1
    idx = max(0, min(idx, len(sorted_values) - 1))
    return sorted_values[idx]


def summary(values_us):
    values = sorted(values_us)
    if not values:
        return {
            "count": 0,
            "avg": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p99": 0.0,
            "p999": 0.0,
            "max": 0.0,
        }
    return {
        "count": len(values),
        "avg": sum(values) / len(values),
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p99": percentile(values, 0.99),
        "p999": percentile(values, 0.999),
        "max": values[-1],
    }


def histogram(values, bins=80):
    if not values:
        return []
    lo = 0.0
    hi = percentile(sorted(values), 0.999)
    if hi <= lo:
        hi = max(values)
    if hi <= lo:
        hi = 1.0
    width = (hi - lo) / bins
    counts = [0] * bins
    overflow = 0
    for value in values:
        if value > hi:
            overflow += 1
            continue
        idx = int((value - lo) / width)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1
    return [(lo + i * width, lo + (i + 1) * width, counts[i]) for i in range(bins)], overflow


def write_svg(path, title, values_us):
    width = 1000
    height = 520
    margin_left = 80
    margin_right = 30
    margin_top = 70
    margin_bottom = 70
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    hist, overflow = histogram(values_us)
    max_count = max([row[2] for row in hist], default=1)
    stats = summary(values_us)

    with open(path, "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n')
        f.write('<rect width="100%" height="100%" fill="white"/>\n')
        f.write(f'<text x="{margin_left}" y="32" font-family="monospace" font-size="22">{title}</text>\n')
        f.write(
            f'<text x="{margin_left}" y="56" font-family="monospace" font-size="13">'
            f'count={stats["count"]} avg={stats["avg"]:.2f}us p50={stats["p50"]:.2f}us '
            f'p90={stats["p90"]:.2f}us p99={stats["p99"]:.2f}us p999={stats["p999"]:.2f}us '
            f'max={stats["max"]:.2f}us overflow_gt_p999={overflow}</text>\n'
        )
        f.write(f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="black"/>\n')
        f.write(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="black"/>\n')
        if hist:
            bar_w = plot_w / len(hist)
            for i, (start, end, count) in enumerate(hist):
                bar_h = 0 if max_count == 0 else (count / max_count) * plot_h
                x = margin_left + i * bar_w
                y = margin_top + plot_h - bar_h
                f.write(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(1, bar_w - 1):.2f}" height="{bar_h:.2f}" fill="#4b7bec"/>\n')
            f.write(f'<text x="{margin_left}" y="{height - 28}" font-family="monospace" font-size="13">0 us</text>\n')
            f.write(f'<text x="{margin_left + plot_w - 160}" y="{height - 28}" font-family="monospace" font-size="13">p999 range end {hist[-1][1]:.2f} us</text>\n')
        f.write(f'<text transform="translate(24 {margin_top + plot_h / 2}) rotate(-90)" font-family="monospace" font-size="13">count</text>\n')
        f.write(f'<text x="{margin_left + plot_w / 2 - 60}" y="{height - 12}" font-family="monospace" font-size="13">latency (us)</text>\n')
        f.write("</svg>\n")


def write_matplotlib_plots(output_dir, run_label, metric_values):
    if not HAVE_MATPLOTLIB:
        return []

    generated = []
    colors = {"Q2D": "#3867d6", "D2C": "#20bf6b", "Q2C": "#eb3b5a"}

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    for name, values in metric_values.items():
        if not values:
            continue
        sorted_values = np.sort(np.asarray(values, dtype=float))
        y = np.arange(1, len(sorted_values) + 1) / len(sorted_values)
        ax.plot(sorted_values, y, label=f"{name} n={len(sorted_values)}", color=colors.get(name))
    ax.set_title(f"{run_label} block I/O latency CDF")
    ax.set_xlabel("Latency (us)")
    ax.set_ylabel("CDF")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    ax.set_xscale("log")
    fig.tight_layout()
    path = output_dir / f"{run_label}.latency_cdf.png"
    fig.savefig(path)
    plt.close(fig)
    generated.append(path)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    for name, values in metric_values.items():
        if not values:
            continue
        arr = np.asarray(values, dtype=float)
        upper = np.percentile(arr, 99.9)
        arr = arr[arr <= upper]
        if arr.size == 0:
            continue
        bins = np.logspace(np.log10(max(arr.min(), 0.001)), np.log10(max(arr.max(), 0.002)), 80)
        ax.hist(arr, bins=bins, histtype="step", linewidth=1.6, label=name, color=colors.get(name))
    ax.set_title(f"{run_label} block I/O latency histogram, clipped at p99.9")
    ax.set_xlabel("Latency (us)")
    ax.set_ylabel("Count")
    ax.set_xscale("log")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    path = output_dir / f"{run_label}.latency_hist_log.png"
    fig.savefig(path)
    plt.close(fig)
    generated.append(path)

    labels = ["p50", "p90", "p99", "p999", "max"]
    x = np.arange(len(labels))
    width = 0.25
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    for offset, name in zip([-width, 0, width], ["Q2D", "D2C", "Q2C"]):
        values = metric_values.get(name, [])
        stats = summary(values)
        heights = [stats["p50"], stats["p90"], stats["p99"], stats["p999"], stats["max"]]
        ax.bar(x + offset, heights, width, label=name, color=colors.get(name))
    ax.set_title(f"{run_label} block I/O latency percentiles")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Latency (us)")
    ax.set_yscale("log")
    ax.grid(True, axis="y", which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    path = output_dir / f"{run_label}.latency_percentiles.png"
    fig.savefig(path)
    plt.close(fig)
    generated.append(path)

    return generated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--q2d-glob", required=True)
    parser.add_argument("--d2c-glob", required=True)
    parser.add_argument("--q2c-glob", required=True)
    parser.add_argument("--aqd-glob", default="")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / f"{args.run_label}.btt_latency_summary.csv"

    rows = []
    metric_values = {}
    for name, pattern in [("Q2D", args.q2d_glob), ("D2C", args.d2c_glob), ("Q2C", args.q2c_glob)]:
        files, raw_values = read_numeric_values(pattern)
        values_us = to_us(raw_values)
        metric_values[name] = values_us
        stats = summary(values_us)
        rows.append((name, pattern, files, stats))
        if not args.no_plots:
            write_svg(output_dir / f"{args.run_label}.{name.lower()}_hist.svg", f"{args.run_label} {name} latency histogram", values_us)

    png_paths = [] if args.no_plots else write_matplotlib_plots(output_dir, args.run_label, metric_values)

    with open(summary_path, "w") as f:
        f.write("run_label,metric,count,avg_us,p50_us,p90_us,p99_us,p999_us,max_us,source_files\n")
        for name, pattern, files, stats in rows:
            f.write(
                f'{args.run_label},{name},{stats["count"]},{stats["avg"]:.6f},{stats["p50"]:.6f},'
                f'{stats["p90"]:.6f},{stats["p99"]:.6f},{stats["p999"]:.6f},{stats["max"]:.6f},'
                f'"{";".join(files)}"\n'
            )

    print(summary_path)
    for name in ("q2d", "d2c", "q2c"):
        print(output_dir / f"{args.run_label}.{name}_hist.svg")
    for path in png_paths:
        print(path)


if __name__ == "__main__":
    main()
