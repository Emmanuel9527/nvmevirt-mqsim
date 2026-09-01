#!/usr/bin/env python3
import csv
import pathlib
import sys

import matplotlib.pyplot as plt


def load_rows(path):
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "target": row["target"],
                    "qd": int(row["qd"]),
                    "repeats": int(row.get("repeats", "1")),
                    "iops": float(row["iops"]),
                    "iops_std": float(row.get("iops_std", "0")),
                    "mean_us": float(row["mean_us"]),
                    "mean_us_std": float(row.get("mean_us_std", "0")),
                    "p99_us": float(row["p99_us"]),
                    "p99_us_std": float(row.get("p99_us_std", "0")),
                    "p999_us": float(row["p999_us"]),
                    "p999_us_std": float(row.get("p999_us_std", "0")),
                    "p9999_us": float(row["p9999_us"]),
                    "max_us": float(row["max_us"]),
                }
            )
    return rows


def series_by_target(rows):
    out = {}
    for row in rows:
        out.setdefault(row["target"], []).append(row)
    for target in out:
        out[target].sort(key=lambda r: r["qd"])
    return out


def label_name(target):
    return {
        "real_ssd": "Real SSD",
        "sim_ssd": "Simulated SSD",
    }.get(target, target)


def plot_one(groups, y_key, title, ylabel, out_path, log_y=False):
    plt.figure(figsize=(9, 5.2))
    for target, rows in groups.items():
        qd = [r["qd"] for r in rows]
        values = [r[y_key] for r in rows]
        style = "--" if target == "real_ssd" else "-"
        marker = "s" if target == "real_ssd" else "o"
        color = "black" if target == "real_ssd" else None
        yerr_key = f"{y_key}_std"
        yerr = [r.get(yerr_key, 0.0) for r in rows]
        if any(v > 0 for v in yerr):
            plt.errorbar(
                qd, values, yerr=yerr, linestyle=style, marker=marker, linewidth=2.2,
                capsize=4, label=f"{label_name(target)} mean", color=color
            )
        else:
            plt.plot(qd, values, linestyle=style, marker=marker, linewidth=2.2, label=label_name(target), color=color)

    plt.title(title)
    plt.xlabel("Queue Depth")
    plt.ylabel(ylabel)
    plt.xticks([1, 4, 8, 16, 32])
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
        qd = [r["qd"] for r in rows]
        style = "--" if target == "real_ssd" else "-"
        color = "black" if target == "real_ssd" else None
        p99_yerr = [r.get("p99_us_std", 0.0) for r in rows]
        p999_yerr = [r.get("p999_us_std", 0.0) for r in rows]
        if any(v > 0 for v in p99_yerr):
            plt.errorbar(qd, [r["p99_us"] for r in rows], yerr=p99_yerr, linestyle=style, marker="o",
                         linewidth=2.0, capsize=4, label=f"{label_name(target)} P99 mean", color=color)
        else:
            plt.plot(qd, [r["p99_us"] for r in rows], linestyle=style, marker="o", linewidth=2.0,
                     label=f"{label_name(target)} P99", color=color)
        if any(v > 0 for v in p999_yerr):
            plt.errorbar(qd, [r["p999_us"] for r in rows], yerr=p999_yerr, linestyle=style, marker="s",
                         linewidth=2.0, capsize=4, label=f"{label_name(target)} P99.9 mean", color=color, alpha=0.72)
        else:
            plt.plot(qd, [r["p999_us"] for r in rows], linestyle=style, marker="s", linewidth=2.0,
                     label=f"{label_name(target)} P99.9", color=color, alpha=0.72)

    plt.title("Fixed Random Read Tail Latency")
    plt.xlabel("Queue Depth")
    plt.ylabel("Latency (us)")
    plt.xticks([1, 4, 8, 16, 32])
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
        "Fixed Random Read Mean Latency",
        "Mean Read Latency (us)",
        out_dir / "fixed_randread_mean_latency.png",
    )
    plot_tail(groups, out_dir / "fixed_randread_tail_latency.png")
    plot_one(
        groups,
        "iops",
        "Fixed Random Read IOPS",
        "IOPS",
        out_dir / "fixed_randread_iops.png",
    )


if __name__ == "__main__":
    raise SystemExit(main())
