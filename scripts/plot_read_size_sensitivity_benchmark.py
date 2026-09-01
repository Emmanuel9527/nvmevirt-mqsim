#!/usr/bin/env python3
import csv
import pathlib
import sys

import matplotlib.pyplot as plt


def bs_to_bytes(bs):
    unit = bs[-1].lower()
    value = float(bs[:-1])
    scale = {"k": 1024, "m": 1024 * 1024, "g": 1024 * 1024 * 1024}.get(unit, 1)
    return int(value * scale)


def load_rows(path):
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "target": row["target"],
                    "bs": row["bs"],
                    "bs_bytes": bs_to_bytes(row["bs"]),
                    "qd": int(row["qd"]),
                    "repeats": int(row.get("repeats", "1")),
                    "iops": float(row["iops"]),
                    "iops_std": float(row.get("iops_std", "0")),
                    "bw_mib_s": float(row["bw_mib_s"]),
                    "bw_mib_s_std": float(row.get("bw_mib_s_std", "0")),
                    "mean_us": float(row["mean_us"]),
                    "mean_us_std": float(row.get("mean_us_std", "0")),
                    "p99_us": float(row["p99_us"]),
                    "p99_us_std": float(row.get("p99_us_std", "0")),
                    "p999_us": float(row["p999_us"]),
                    "p999_us_std": float(row.get("p999_us_std", "0")),
                }
            )
    return rows


def series_by_target(rows):
    out = {}
    for row in rows:
        out.setdefault(row["target"], []).append(row)
    for target in out:
        out[target].sort(key=lambda r: r["bs_bytes"])
    return out


def label_name(target):
    return {
        "real_ssd": "Real SSD mean",
        "sim_ssd": "Simulated SSD",
    }.get(target, target)


def draw_series(rows, y_key, label, style, marker, color=None, alpha=1.0):
    x = [r["bs"] for r in rows]
    y = [r[y_key] for r in rows]
    yerr = [r.get(f"{y_key}_std", 0.0) for r in rows]
    if any(v > 0 for v in yerr):
        plt.errorbar(x, y, yerr=yerr, linestyle=style, marker=marker, linewidth=2.2,
                     capsize=4, label=label, color=color, alpha=alpha)
    else:
        plt.plot(x, y, linestyle=style, marker=marker, linewidth=2.2,
                 label=label, color=color, alpha=alpha)


def plot_one(groups, y_key, title, ylabel, out_path, log_y=False):
    plt.figure(figsize=(9, 5.2))
    for target, rows in groups.items():
        style = "--" if target == "real_ssd" else "-"
        marker = "s" if target == "real_ssd" else "o"
        color = "black" if target == "real_ssd" else None
        draw_series(rows, y_key, label_name(target), style, marker, color=color)
    plt.title(title)
    plt.xlabel("Read Size")
    plt.ylabel(ylabel)
    if log_y:
        plt.yscale("log")
    plt.grid(True, alpha=0.28)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_tail(groups, out_path):
    plt.figure(figsize=(9, 5.2))
    for target, rows in groups.items():
        style = "--" if target == "real_ssd" else "-"
        color = "black" if target == "real_ssd" else None
        draw_series(rows, "p99_us", f"{label_name(target)} P99", style, "o", color=color)
        draw_series(rows, "p999_us", f"{label_name(target)} P99.9", style, "s", color=color, alpha=0.72)
    plt.title("Read-Size Sensitivity Tail Latency")
    plt.xlabel("Read Size")
    plt.ylabel("Latency (us)")
    plt.yscale("log")
    plt.grid(True, alpha=0.28)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} summary.csv out_dir", file=sys.stderr)
        return 2

    csv_path = pathlib.Path(sys.argv[1])
    out_dir = pathlib.Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = series_by_target(load_rows(csv_path))

    plot_one(
        groups,
        "mean_us",
        "Read-Size Sensitivity Mean Latency",
        "Mean Read Latency (us)",
        out_dir / "read_size_sensitivity_mean_latency.png",
    )
    plot_tail(groups, out_dir / "read_size_sensitivity_tail_latency.png")
    plot_one(
        groups,
        "bw_mib_s",
        "Read-Size Sensitivity Bandwidth",
        "Bandwidth (MiB/s)",
        out_dir / "read_size_sensitivity_bandwidth.png",
    )


if __name__ == "__main__":
    raise SystemExit(main())
