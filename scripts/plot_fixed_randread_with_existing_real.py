#!/usr/bin/env python3
import csv
import os
import pathlib
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def select_rows(rows, target):
    selected = []
    for row in rows:
        if row["target"] != target:
            continue
        selected.append(
            {
                "target": target,
                "qd": int(row["qd"]),
                "repeats": int(row.get("repeats", "1")),
                "iops": float(row["iops"]),
                "iops_std": float(row.get("iops_std", "0")),
                "mean_us": float(row["mean_us"]),
                "mean_us_std": float(row.get("mean_us_std", "0")),
                "p999_us": float(row["p999_us"]),
                "p999_us_std": float(row.get("p999_us_std", "0")),
            }
        )
    return sorted(selected, key=lambda row: row["qd"])


def write_combined(rows, out_csv):
    with open(out_csv, "w", newline="") as f:
        fieldnames = [
            "target", "qd", "repeats",
            "iops", "iops_std",
            "mean_us", "mean_us_std",
            "p999_us", "p999_us_std",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def plot_one(real_rows, sim_rows, y_key, y_std_key, title, ylabel, out_path):
    plt.figure(figsize=(9, 5.2))

    plt.errorbar(
        [r["qd"] for r in real_rows],
        [r[y_key] for r in real_rows],
        yerr=[r[y_std_key] for r in real_rows],
        linestyle="--",
        marker="s",
        color="black",
        linewidth=2.2,
        capsize=4,
        label=f"Real SSD mean ({real_rows[0]['repeats']} runs)",
    )
    plt.plot(
        [r["qd"] for r in sim_rows],
        [r[y_key] for r in sim_rows],
        linestyle="-",
        marker="o",
        linewidth=2.2,
        label="Simulated SSD after event-order fix",
    )

    plt.title(title)
    plt.xlabel("Queue Depth")
    plt.ylabel(ylabel)
    plt.xticks([1, 4, 8, 16, 32])
    plt.grid(True, alpha=0.28)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def main():
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} OLD_REAL_SUMMARY NEW_SIM_SUMMARY OUT_DIR",
            file=sys.stderr,
        )
        return 2

    old_real_summary = pathlib.Path(sys.argv[1])
    new_sim_summary = pathlib.Path(sys.argv[2])
    out_dir = pathlib.Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    real_rows = select_rows(read_rows(old_real_summary), "real_ssd")
    sim_rows = select_rows(read_rows(new_sim_summary), "sim_ssd")
    if not real_rows:
        raise SystemExit(f"No real_ssd rows found in {old_real_summary}")
    if not sim_rows:
        raise SystemExit(f"No sim_ssd rows found in {new_sim_summary}")

    combined = real_rows + sim_rows
    write_combined(combined, out_dir / "fixed_randread_after_event_fix_vs_real10.csv")
    plot_one(
        real_rows,
        sim_rows,
        "mean_us",
        "mean_us_std",
        "Fixed Random Read Mean Latency",
        "Mean Read Latency (us)",
        out_dir / "fixed_randread_after_event_fix_mean_latency.png",
    )
    plot_one(
        real_rows,
        sim_rows,
        "p999_us",
        "p999_us_std",
        "Fixed Random Read P99.9 Latency",
        "P99.9 Read Latency (us)",
        out_dir / "fixed_randread_after_event_fix_p999_latency.png",
    )
    plot_one(
        real_rows,
        sim_rows,
        "iops",
        "iops_std",
        "Fixed Random Read IOPS",
        "IOPS",
        out_dir / "fixed_randread_after_event_fix_iops.png",
    )


if __name__ == "__main__":
    raise SystemExit(main())
