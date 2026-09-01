#!/usr/bin/env python3
import argparse
import csv
import math
import os
import pathlib
import statistics

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")


def read_perf_rows(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if parts and parts[0].isdigit():
            rows.append({
                "L": int(parts[0]),
                "Beamwidth": int(parts[1]),
                "QPS": float(parts[2]),
                "MeanLatency_us": float(parts[3]),
                "P999Latency_us": float(parts[4]),
                "MeanIOs": float(parts[5]),
                "MeanIO_us": float(parts[6]),
                "CPU_s": float(parts[7]),
                "CacheHits": float(parts[8]),
                "MeanHops": float(parts[9]),
                "CacheHitRate": float(parts[10]),
                "Recall10": float(parts[11]),
            })
    return rows


def mean(values):
    return statistics.fmean(values) if values else 0.0


def stdev(values):
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def stderr(values):
    return stdev(values) / math.sqrt(len(values)) if values else 0.0


def summarize(result_root, index_variant, w, t, cache):
    runs = sorted(p for p in result_root.iterdir() if p.is_dir() and p.name.startswith("run_"))
    by_l = {}
    by_run = {}
    for run_dir in runs:
        summary = run_dir / f"{index_variant}_L_sweep_W{w}_T{t}_cache{cache}.performance_summary.txt"
        rows = read_perf_rows(summary)
        if rows:
            by_run[run_dir.name] = sorted(rows, key=lambda row: row["L"])
        for row in rows:
            by_l.setdefault(row["L"], []).append(row)
    return runs, by_run, by_l


def write_summary(out_csv, runs, by_l):
    fields = [
        "L", "Repeats",
        "MeanLatency_avg_us", "MeanLatency_std_us", "MeanLatency_stderr_us",
        "MeanIO_avg_us", "MeanIO_std_us", "MeanIO_stderr_us",
        "P999Latency_avg_us", "P999Latency_std_us",
        "QPS_avg", "QPS_std",
        "MeanIOs_avg", "MeanHops_avg", "Recall10_avg",
    ]
    rows = []
    for l_value in sorted(by_l):
        entries = by_l[l_value]
        mean_lat = [r["MeanLatency_us"] for r in entries]
        mean_io = [r["MeanIO_us"] for r in entries]
        p999 = [r["P999Latency_us"] for r in entries]
        qps = [r["QPS"] for r in entries]
        rows.append({
            "L": l_value,
            "Repeats": len(entries),
            "MeanLatency_avg_us": mean(mean_lat),
            "MeanLatency_std_us": stdev(mean_lat),
            "MeanLatency_stderr_us": stderr(mean_lat),
            "MeanIO_avg_us": mean(mean_io),
            "MeanIO_std_us": stdev(mean_io),
            "MeanIO_stderr_us": stderr(mean_io),
            "P999Latency_avg_us": mean(p999),
            "P999Latency_std_us": stdev(p999),
            "QPS_avg": mean(qps),
            "QPS_std": stdev(qps),
            "MeanIOs_avg": mean([r["MeanIOs"] for r in entries]),
            "MeanHops_avg": mean([r["MeanHops"] for r in entries]),
            "Recall10_avg": mean([r["Recall10"] for r in entries]),
        })

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def print_table(rows):
    print("Real SSD repeated-run summary:")
    print(
        f"{'L':>6} {'N':>4} {'MeanLatAvg':>12} {'MeanLatStd':>12} "
        f"{'MeanIOAvg':>11} {'MeanIOStd':>11} {'P999Avg':>10} {'QPSAvg':>9}"
    )
    print("=" * 86)
    for row in rows:
        print(
            f"{row['L']:6d} {row['Repeats']:4d} "
            f"{row['MeanLatency_avg_us']:12.2f} {row['MeanLatency_std_us']:12.2f} "
            f"{row['MeanIO_avg_us']:11.2f} {row['MeanIO_std_us']:11.2f} "
            f"{row['P999Latency_avg_us']:10.2f} {row['QPS_avg']:9.2f}"
        )


def print_each_run_tables(by_run):
    for run_name in sorted(by_run):
        rows = by_run[run_name]
        print()
        print(f"DiskANN performance table: {run_name}")
        print(
            f"{'L':>6} {'Beamwidth':>11} {'QPS':>15} {'Mean Latency':>15} "
            f"{'99.9 Latency':>16} {'Mean IOs':>15} {'Mean IO (us)':>16} "
            f"{'CPU (s)':>15} {'Cache Hits':>15} {'Mean Hops':>15} "
            f"{'Cache Hit Rate':>15} {'Recall@10':>15}"
        )
        print("=" * 180)
        for row in rows:
            print(
                f"{row['L']:6d} {row['Beamwidth']:11d} {row['QPS']:15.2f} "
                f"{row['MeanLatency_us']:15.2f} {row['P999Latency_us']:16.2f} "
                f"{row['MeanIOs']:15.2f} {row['MeanIO_us']:16.2f} "
                f"{row['CPU_s']:15.2f} {row['CacheHits']:15.2f} {row['MeanHops']:15.2f} "
                f"{row['CacheHitRate']:15.2f} {row['Recall10']:15.2f}"
            )


def write_per_run_csv(out_csv, by_run):
    fields = [
        "run", "L", "Beamwidth", "QPS", "MeanLatency_us", "P999Latency_us", "MeanIOs",
        "MeanIO_us", "CPU_s", "CacheHits", "MeanHops", "CacheHitRate", "Recall10",
    ]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for run_name in sorted(by_run):
            for row in by_run[run_name]:
                writer.writerow({"run": run_name, **row})


def plot_repeated_runs(plot_dir, by_run):
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"matplotlib unavailable, skip plots: {exc}")
        return []

    plot_dir.mkdir(parents=True, exist_ok=True)
    cmap = plt.get_cmap("tab20")
    outputs = []

    metrics = [
        ("MeanLatency_us", "Mean Latency by L", "Mean Latency (us)", "real_ssd_repeats_mean_latency.png"),
        ("MeanIO_us", "Mean IO by L", "Mean IO (us)", "real_ssd_repeats_meanio.png"),
    ]
    for metric, title, ylabel, filename in metrics:
        fig, ax = plt.subplots(figsize=(9.5, 5.5))
        for idx, run_name in enumerate(sorted(by_run)):
            rows = by_run[run_name]
            l_values = [row["L"] for row in rows]
            values = [row[metric] for row in rows]
            ax.plot(
                l_values,
                values,
                marker="o",
                linewidth=2,
                color=cmap(idx % cmap.N),
                label=run_name,
            )
        ax.set_title(title)
        ax.set_xlabel("L")
        ax.set_ylabel(ylabel)
        ax.set_xticks([20, 40, 60, 80, 100, 120])
        ax.grid(True, alpha=0.3)
        ax.legend(ncol=2)
        fig.tight_layout()
        out_path = plot_dir / filename
        fig.savefig(out_path, dpi=180)
        plt.close(fig)
        outputs.append(out_path)
    return outputs


def main():
    parser = argparse.ArgumentParser(description="Aggregate repeated real SSD DiskANN runs.")
    parser.add_argument("--result-root", type=pathlib.Path, default=pathlib.Path("/home/emmanuel/projects/DiskANN_cpp/results/real_ssd_latency_repeats"))
    parser.add_argument("--index-variant", default="block_shuffle")
    parser.add_argument("--w", default="16")
    parser.add_argument("--t", default="1")
    parser.add_argument("--cache", default="0")
    parser.add_argument("--out-csv", type=pathlib.Path)
    parser.add_argument("--out-runs-csv", type=pathlib.Path)
    parser.add_argument("--plot-dir", type=pathlib.Path)
    args = parser.parse_args()

    runs, by_run, by_l = summarize(args.result_root, args.index_variant, args.w, args.t, args.cache)
    if not runs:
        raise SystemExit(f"No run_* directories found under {args.result_root}")
    if not by_l:
        raise SystemExit(f"No performance summaries found under {args.result_root}")

    out_csv = args.out_csv or (args.result_root / f"{args.index_variant}_L_sweep_W{args.w}_T{args.t}_cache{args.cache}.repeat_summary.csv")
    out_runs_csv = args.out_runs_csv or (args.result_root / f"{args.index_variant}_L_sweep_W{args.w}_T{args.t}_cache{args.cache}.repeat_runs.csv")
    plot_dir = args.plot_dir or (args.result_root / "repeat_plots")
    rows = write_summary(out_csv, runs, by_l)
    write_per_run_csv(out_runs_csv, by_run)
    plot_paths = plot_repeated_runs(plot_dir, by_run)
    print_each_run_tables(by_run)
    print()
    print_table(rows)
    print(f"Saved: {out_csv}")
    print(f"Saved: {out_runs_csv}")
    for path in plot_paths:
        print(f"Saved: {path}")


if __name__ == "__main__":
    main()
