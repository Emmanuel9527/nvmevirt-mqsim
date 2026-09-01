#!/usr/bin/env python3
import csv
import os
import pathlib

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

import matplotlib.pyplot as plt


RESULT_ROOT = pathlib.Path("/home/emmanuel/projects/DiskANN_cpp/results")
OUT_DIR = pathlib.Path("plots")
OUT_PNG = OUT_DIR / "meanio_param_sweep.png"
OUT_CSV = OUT_DIR / "meanio_param_sweep.csv"
OUT_MEAN_LATENCY_PNG = OUT_DIR / "mean_latency_param_sweep.png"
OUT_MEAN_LATENCY_CSV = OUT_DIR / "mean_latency_param_sweep.csv"

EXPERIMENTS = [
    ("8ch -> 4ch", RESULT_ROOT / "nvmevirt_mqsim_ch4"),
    ("xfer 333 -> 200", RESULT_ROOT / "nvmevirt_mqsim_ch8_xfer200"),
    ("read 70/100/150us", RESULT_ROOT / "nvmevirt_mqsim_readlat_70_100_150"),
    ("CMT 524288", RESULT_ROOT / "nvmevirt_mqsim_cmt524k"),
    ("die/chip 2 -> 1", RESULT_ROOT / "nvmevirt_mqsim_die1"),
    ("Real SSD", RESULT_ROOT / "real_ssd_latency"),
]
REAL_SSD_REPEAT_SUMMARY = RESULT_ROOT / "real_ssd_latency_repeats" / "block_shuffle_L_sweep_W16_T1_cache0.repeat_summary.csv"

STYLES = {
    "8ch -> 4ch": {"marker": "o", "linestyle": "-", "linewidth": 2.0},
    "xfer 333 -> 200": {"marker": "o", "linestyle": "-", "linewidth": 2.0},
    "read 70/100/150us": {"marker": "o", "linestyle": "-", "linewidth": 2.0},
    "CMT 524288": {"marker": "D", "linestyle": "--", "linewidth": 2.0},
    "die/chip 2 -> 1": {"marker": "^", "linestyle": ":", "linewidth": 2.8},
    "Real SSD": {"marker": "s", "linestyle": "--", "linewidth": 2.8, "color": "black"},
}


def read_rows(result_dir):
    if result_dir.name == "real_ssd_latency" and REAL_SSD_REPEAT_SUMMARY.exists():
        rows = []
        with REAL_SSD_REPEAT_SUMMARY.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append((
                    int(row["L"]),
                    float(row["MeanLatency_avg_us"]),
                    float(row["MeanIO_avg_us"]),
                    float(row["MeanLatency_std_us"]),
                    float(row["MeanIO_std_us"]),
                ))
        return sorted(rows)

    summary = result_dir / "block_shuffle_L_sweep_W16_T1_cache0.performance_summary.txt"
    if summary.exists():
        files = [summary]
    else:
        files = sorted(result_dir.glob("block_shuffle_L*_W16_T1_cache0.performance_table.txt"))

    rows = []
    for path in files:
        for line in path.read_text(errors="replace").splitlines():
            parts = line.split()
            if parts and parts[0].isdigit():
                rows.append((int(parts[0]), float(parts[3]), float(parts[6]), 0.0, 0.0))
    return sorted(rows)


def plot_metric(metric_name, out_png, out_csv, value_index, y_label):
    all_rows = []

    plt.figure(figsize=(9.5, 5.5))
    for label, result_dir in EXPERIMENTS:
        rows = read_rows(result_dir)
        if not rows:
            raise SystemExit(f"No rows found in {result_dir}")
        l_values = [row[0] for row in rows]
        values = [row[value_index] for row in rows]
        all_rows.extend({"experiment": label, "L": l, metric_name: value} for l, value in zip(l_values, values))
        if label == "Real SSD" and any(row[value_index + 2] > 0 for row in rows):
            errors = [row[value_index + 2] for row in rows]
            plt.errorbar(l_values, values, yerr=errors, capsize=4, label=label, **STYLES[label])
        else:
            plt.plot(l_values, values, label=label, **STYLES[label])

    plt.title(f"{metric_name} by L")
    plt.xlabel("L")
    plt.ylabel(y_label)
    plt.xticks([20, 40, 60, 80, 100, 120])
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=180)
    plt.close()

    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["experiment", "L", metric_name])
        writer.writeheader()
        writer.writerows(all_rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plot_metric("Mean IO", OUT_PNG, OUT_CSV, 2, "Mean IO (us)")
    plot_metric("Mean Latency", OUT_MEAN_LATENCY_PNG, OUT_MEAN_LATENCY_CSV, 1, "Mean Latency (us)")

    print(OUT_PNG)
    print(OUT_CSV)
    print(OUT_MEAN_LATENCY_PNG)
    print(OUT_MEAN_LATENCY_CSV)


if __name__ == "__main__":
    main()
