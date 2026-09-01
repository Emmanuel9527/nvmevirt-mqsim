#!/usr/bin/env python3
import argparse
import csv
import math
import os
import pathlib
import statistics
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")


def read_counter(path, key):
    prefix = f"{key}:"
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == prefix:
            try:
                return int(parts[1])
            except ValueError:
                return 0
    return 0


def delta_counter(before, after, key):
    return read_counter(after, key) - read_counter(before, key)


def delta_avg_ns(before, after, count_key, avg_key):
    before_count = read_counter(before, count_key)
    after_count = read_counter(after, count_key)
    before_avg = read_counter(before, avg_key)
    after_avg = read_counter(after, avg_key)
    delta_count = after_count - before_count
    if delta_count <= 0:
        return 0.0
    delta_total = after_count * after_avg - before_count * before_avg
    return delta_total / delta_count


def read_perf_row(path):
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if parts and parts[0].isdigit():
            return {
                "L": int(parts[0]),
                "QPS": float(parts[2]),
                "MeanLat_us": float(parts[3]),
                "P999Lat_us": float(parts[4]),
                "MeanIOs": float(parts[5]),
                "MeanIO_us": float(parts[6]),
            }
    raise ValueError(f"no performance row found in {path}")


def safe_pct(part, whole):
    if whole <= 0:
        return 0.0
    return 100.0 * part / whole


def load_rows(result_dir, index_variant, l_values, w, t, cache):
    rows = []
    for l_value in l_values:
        run_label = f"{index_variant}_L{l_value}_W{w}_T{t}_cache{cache}"
        perf_file = result_dir / f"{run_label}.performance_table.txt"
        before_file = result_dir / f"{run_label}.mqsim_before.txt"
        after_file = result_dir / f"{run_label}.mqsim_after.txt"
        for path in (perf_file, before_file, after_file):
            if not path.exists():
                raise FileNotFoundError(path)

        perf = read_perf_row(perf_file)
        req_delta = delta_counter(before_file, after_file, "requests")
        reply_delta = delta_counter(before_file, after_file, "replies")
        rt_avg_us = delta_avg_ns(before_file, after_file, "roundtrip_count", "roundtrip_avg_ns") / 1000.0
        submit_avg_us = delta_avg_ns(before_file, after_file, "submit_cost_count", "submit_cost_avg_ns") / 1000.0
        late_delta = delta_counter(before_file, after_file, "reply_late_count")
        late_avg_us = delta_avg_ns(before_file, after_file, "reply_late_count", "reply_late_avg_ns") / 1000.0
        late_all_us = late_avg_us * late_delta / reply_delta if reply_delta > 0 else 0.0

        row = {
            **perf,
            "ReqDelta": req_delta,
            "ReplyDelta": reply_delta,
            "RTAvg_us": rt_avg_us,
            "Submit_us": submit_avg_us,
            "LateCnt": late_delta,
            "LateRate_pct": safe_pct(late_delta, reply_delta),
            "LateAvg_us": late_avg_us,
            "LateAll_us": late_all_us,
            "RTPctMeanIO": safe_pct(rt_avg_us, perf["MeanIO_us"]),
            "SubmitPctMeanIO": safe_pct(submit_avg_us, perf["MeanIO_us"]),
            "LateAllPctMeanIO": safe_pct(late_all_us, perf["MeanIO_us"]),
            "Fallbacks": delta_counter(before_file, after_file, "fallbacks"),
            "SendErr": delta_counter(before_file, after_file, "send_errors"),
            "RingFull": delta_counter(before_file, after_file, "req_ring_full"),
        }
        rows.append(row)
    return rows


def write_csv(path, rows):
    fields = [
        "L", "QPS", "MeanLat_us", "P999Lat_us", "MeanIOs", "MeanIO_us",
        "ReqDelta", "ReplyDelta", "RTAvg_us", "RTPctMeanIO",
        "Submit_us", "SubmitPctMeanIO", "LateCnt", "LateRate_pct",
        "LateAvg_us", "LateAll_us", "LateAllPctMeanIO",
        "Fallbacks", "SendErr", "RingFull",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})


def format_table(rows):
    lines = []
    lines.append("DiskANN MQSim IPC cost ratio table:")
    header = (
        f"{'L':>6} {'QPS':>10} {'MeanIO(us)':>12} {'RT(us)':>10} {'RT/IO%':>10} "
        f"{'Submit(us)':>12} {'Submit/IO%':>12} {'LateRate%':>10} "
        f"{'LateAll(us)':>12} {'LateAll/IO%':>12}"
    )
    lines.append(header)
    lines.append("=" * len(header))
    for row in rows:
        lines.append(
            f"{row['L']:6d} {row['QPS']:10.2f} {row['MeanIO_us']:12.2f} "
            f"{row['RTAvg_us']:10.2f} {row['RTPctMeanIO']:10.2f} "
            f"{row['Submit_us']:12.3f} {row['SubmitPctMeanIO']:12.4f} "
            f"{row['LateRate_pct']:10.4f} {row['LateAll_us']:12.4f} "
            f"{row['LateAllPctMeanIO']:12.4f}"
        )
    return "\n".join(lines) + "\n"


def plot_rows(out_dir, rows, title_prefix):
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"matplotlib unavailable, skip plots: {exc}", file=sys.stderr)
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    l_values = [row["L"] for row in rows]
    plot_paths = []

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(l_values, [row["RTPctMeanIO"] for row in rows], marker="o", label="RTAvg / MeanIO")
    ax.plot(l_values, [row["SubmitPctMeanIO"] for row in rows], marker="o", label="Submit / MeanIO")
    ax.plot(l_values, [row["LateAllPctMeanIO"] for row in rows], marker="o", label="Late reply amortized / MeanIO")
    ax.set_xlabel("DiskANN L")
    ax.set_ylabel("Percent of Mean IO time (%)")
    ax.set_title(f"{title_prefix} IPC cost ratio")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    path = out_dir / "ipc_cost_ratio_by_l.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    plot_paths.append(path)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    width = 0.25
    xs = list(range(len(l_values)))
    ax.bar([x - width for x in xs], [row["RTAvg_us"] for row in rows], width, label="RTAvg")
    ax.bar(xs, [row["Submit_us"] for row in rows], width, label="Submit")
    ax.bar([x + width for x in xs], [row["LateAll_us"] for row in rows], width, label="Late reply amortized")
    ax.set_xticks(xs)
    ax.set_xticklabels([str(v) for v in l_values])
    ax.set_xlabel("DiskANN L")
    ax.set_ylabel("Time (us)")
    ax.set_title(f"{title_prefix} IPC cost in microseconds")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    path = out_dir / "ipc_cost_us_by_l.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    plot_paths.append(path)

    return plot_paths


def parse_l_values(text):
    return [int(part) for part in text.split() if part.strip()]


def main():
    parser = argparse.ArgumentParser(description="Summarize MQSim IPC costs across DiskANN L sweep runs.")
    parser.add_argument("--result-dir", required=True, type=pathlib.Path)
    parser.add_argument("--index-variant", default="block_shuffle")
    parser.add_argument("--l-values", default="20 40 60 80 100 120")
    parser.add_argument("--w", default="16")
    parser.add_argument("--t", default="1")
    parser.add_argument("--cache", default="0")
    parser.add_argument("--out-prefix", type=pathlib.Path)
    parser.add_argument("--plot-dir", type=pathlib.Path)
    args = parser.parse_args()

    rows = load_rows(
        args.result_dir,
        args.index_variant,
        parse_l_values(args.l_values),
        args.w,
        args.t,
        args.cache,
    )
    if not rows:
        raise SystemExit("no rows")

    out_prefix = args.out_prefix
    if out_prefix is None:
        out_prefix = args.result_dir / f"{args.index_variant}_L_sweep_W{args.w}_T{args.t}_cache{args.cache}.ipc_ratio"
    plot_dir = args.plot_dir or (args.result_dir / "ipc_plots")

    table_path = out_prefix.with_suffix(".txt")
    csv_path = out_prefix.with_suffix(".csv")
    table = format_table(rows)
    table_path.write_text(table)
    write_csv(csv_path, rows)
    plot_paths = plot_rows(plot_dir, rows, "DiskANN MQSim")

    print(table, end="")
    print("Saved IPC ratio summary:")
    print(f"  {table_path}")
    print(f"  {csv_path}")
    for path in plot_paths:
        print(f"  {path}")


if __name__ == "__main__":
    main()
