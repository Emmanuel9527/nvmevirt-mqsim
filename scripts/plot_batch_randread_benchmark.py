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
                    "batch_size": int(row["batch_size"]),
                    "repeats": int(row.get("repeats", "1")),
                    "iops": float(row["iops"]),
                    "iops_std": float(row.get("iops_std", "0")),
                    "io_mean_us": float(row["io_mean_us"]),
                    "io_mean_us_std": float(row.get("io_mean_us_std", "0")),
                    "batch_mean_us": float(row["batch_mean_us"]),
                    "batch_mean_us_std": float(row.get("batch_mean_us_std", "0")),
                    "io_p999_us": float(row["io_p999_us"]),
                    "io_p999_us_std": float(row.get("io_p999_us_std", "0")),
                    "batch_first_mean_us": float(row.get("batch_first_mean_us", "0")),
                    "batch_first_mean_us_std": float(row.get("batch_first_mean_us_std", "0")),
                    "batch_p999_us": float(row["batch_p999_us"]),
                    "batch_p999_us_std": float(row.get("batch_p999_us_std", "0")),
                    "batch_spread_mean_us": float(row.get("batch_spread_mean_us", "0")),
                    "batch_spread_mean_us_std": float(row.get("batch_spread_mean_us_std", "0")),
                }
            )
    return rows


def label_name(target):
    return {
        "real_ssd": "Real SSD mean",
        "sim_ssd": "Simulated SSD",
    }.get(target, target)


def draw_bar(rows, y_key, title, ylabel, out_path, log_y=False):
    multiple_batches = len({r["batch_size"] for r in rows}) > 1
    labels = [
        f'{label_name(r["target"])}\nbatch={r["batch_size"]}' if multiple_batches else label_name(r["target"])
        for r in rows
    ]
    values = [r[y_key] for r in rows]
    yerr = [r.get(f"{y_key}_std", 0.0) for r in rows]
    colors = ["black" if r["target"] == "real_ssd" else "#1f77b4" for r in rows]

    plt.figure(figsize=(7.2, 5.0))
    plt.bar(labels, values, yerr=yerr if any(v > 0 for v in yerr) else None,
            capsize=5, color=colors, alpha=0.82)
    plt.title(title)
    plt.ylabel(ylabel)
    if log_y:
        plt.yscale("log")
    plt.grid(True, axis="y", alpha=0.28)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def draw_batch_sweep(rows, y_key, title, ylabel, out_path, log_y=False):
    targets = sorted({r["target"] for r in rows}, key=lambda t: 0 if t == "real_ssd" else 1)
    colors = {"real_ssd": "black", "sim_ssd": "#1f77b4"}
    markers = {"real_ssd": "s", "sim_ssd": "o"}

    fig, ax = plt.subplots(figsize=(9, 5.2))
    for target in targets:
        target_rows = sorted([r for r in rows if r["target"] == target], key=lambda r: r["batch_size"])
        x = [r["batch_size"] for r in target_rows]
        y = [r[y_key] for r in target_rows]
        yerr = [r.get(f"{y_key}_std", 0.0) for r in target_rows]
        linestyle = "--" if target == "real_ssd" else "-"
        ax.errorbar(
            x,
            y,
            yerr=yerr if any(v > 0 for v in yerr) else None,
            fmt=markers.get(target, "o") + linestyle,
            color=colors.get(target),
            capsize=4,
            label=label_name(target),
        )

    ax.set_title(title)
    ax.set_xlabel("Batch Size")
    ax.set_ylabel(ylabel)
    ax.set_xticks(sorted({r["batch_size"] for r in rows}))
    if log_y:
        ax.set_yscale("log")
    ax.grid(True, alpha=0.28)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def draw_bar_on_axis(ax, rows, y_key, title, ylabel, log_y=False):
    labels = [label_name(r["target"]) for r in rows]
    values = [r[y_key] for r in rows]
    yerr = [r.get(f"{y_key}_std", 0.0) for r in rows]
    colors = ["black" if r["target"] == "real_ssd" else "#1f77b4" for r in rows]

    ax.bar(labels, values, yerr=yerr if any(v > 0 for v in yerr) else None,
           capsize=5, color=colors, alpha=0.82)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    if log_y:
        ax.set_yscale("log")
    ax.grid(True, axis="y", alpha=0.28)


def draw_combined(rows, out_path):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    draw_bar_on_axis(
        axes[0, 0],
        rows,
        "io_mean_us",
        "Per-I/O Mean Latency",
        "Latency (us)",
    )
    draw_bar_on_axis(
        axes[0, 1],
        rows,
        "batch_mean_us",
        "Batch Mean Latency",
        "Latency (us)",
    )
    draw_bar_on_axis(
        axes[1, 0],
        rows,
        "iops",
        "IOPS",
        "IOPS",
    )
    draw_bar_on_axis(
        axes[1, 1],
        rows,
        "batch_p999_us",
        "Batch P99.9 Latency",
        "Latency (us, log scale)",
        log_y=True,
    )
    fig.suptitle("Batch Random Read Benchmark", fontsize=15)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def draw_shared_axes(rows, out_path):
    metrics = [
        ("io_mean_us", "Per-I/O mean latency"),
        ("batch_first_mean_us", "Batch first-completion latency"),
        ("batch_mean_us", "Batch mean latency"),
        ("batch_spread_mean_us", "Batch completion spread"),
        ("batch_p999_us", "Batch P99.9 latency"),
    ]
    targets = ["real_ssd", "sim_ssd"]
    by_target = {row["target"]: row for row in rows}
    x = list(range(len(metrics)))
    width = 0.36
    offsets = {"real_ssd": -width / 2, "sim_ssd": width / 2}
    colors = {"real_ssd": "black", "sim_ssd": "#1f77b4"}

    fig, ax = plt.subplots(figsize=(11, 5.8))
    for target in targets:
        if target not in by_target:
            continue
        row = by_target[target]
        values = [row[key] for key, _ in metrics]
        yerr = [row.get(f"{key}_std", 0.0) for key, _ in metrics]
        ax.bar(
            [i + offsets[target] for i in x],
            values,
            width,
            yerr=yerr if any(v > 0 for v in yerr) else None,
            capsize=4,
            color=colors[target],
            alpha=0.82,
            label=label_name(target),
        )

    ax.set_title("Batch Random Read Benchmark")
    ax.set_ylabel("Latency (us)")
    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in metrics])
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def draw_ratio(rows, out_path):
    metrics = [
        ("io_mean_us", "Per-I/O mean latency"),
        ("batch_first_mean_us", "Batch first-completion latency"),
        ("batch_mean_us", "Batch mean latency"),
        ("batch_spread_mean_us", "Batch completion spread"),
        ("batch_p999_us", "Batch P99.9 latency"),
    ]
    by_target = {row["target"]: row for row in rows}
    if "real_ssd" not in by_target or "sim_ssd" not in by_target:
        return

    real = by_target["real_ssd"]
    sim = by_target["sim_ssd"]
    labels = [label for _, label in metrics]
    ratios = [sim[key] / real[key] if real[key] else 0.0 for key, _ in metrics]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(labels, ratios, color="#1f77b4", alpha=0.82)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1.4, label="Real SSD baseline")
    ax.set_title("Batch Random Read Simulator / Real SSD Ratio")
    ax.set_ylabel("Simulated SSD / Real SSD")
    ax.tick_params(axis="x", labelrotation=12)
    for tick in ax.get_xticklabels():
        tick.set_ha("right")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} summary.csv out_dir", file=sys.stderr)
        return 2

    csv_path = pathlib.Path(sys.argv[1])
    out_dir = pathlib.Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(csv_path)
    multiple_batches = len({r["batch_size"] for r in rows}) > 1

    draw_bar(
        rows,
        "io_mean_us",
        "Batch Random Read Per-I/O Mean Latency",
        "Per-I/O Mean Latency (us)",
        out_dir / "batch_randread_io_mean_latency.png",
    )
    draw_bar(
        rows,
        "batch_first_mean_us",
        "Batch Random Read First Completion Latency",
        "First Completion Latency (us)",
        out_dir / "batch_randread_first_completion_latency.png",
    )
    draw_bar(
        rows,
        "batch_mean_us",
        "Batch Random Read Batch Mean Latency",
        "Batch Mean Latency (us)",
        out_dir / "batch_randread_batch_mean_latency.png",
    )
    draw_bar(
        rows,
        "batch_spread_mean_us",
        "Batch Random Read Completion Spread",
        "Last - First Completion (us)",
        out_dir / "batch_randread_completion_spread.png",
    )
    draw_bar(
        rows,
        "iops",
        "Batch Random Read IOPS",
        "IOPS",
        out_dir / "batch_randread_iops.png",
    )
    draw_bar(
        rows,
        "batch_p999_us",
        "Batch Random Read Batch P99.9 Latency",
        "Batch P99.9 Latency (us)",
        out_dir / "batch_randread_batch_p999_latency.png",
        log_y=True,
    )
    draw_combined(rows, out_dir / "batch_randread_combined.png")
    draw_shared_axes(rows, out_dir / "batch_randread_combined_shared_axes.png")
    draw_ratio(rows, out_dir / "batch_randread_sim_real_ratio.png")

    if multiple_batches:
        draw_batch_sweep(
            rows,
            "io_mean_us",
            "Batch Random Read Per-I/O Mean Latency",
            "Per-I/O Mean Latency (us)",
            out_dir / "batch_randread_io_mean_latency_by_batch_size.png",
        )
        draw_batch_sweep(
            rows,
            "batch_first_mean_us",
            "Batch Random Read First Completion Latency",
            "First Completion Latency (us)",
            out_dir / "batch_randread_first_completion_latency_by_batch_size.png",
        )
        draw_batch_sweep(
            rows,
            "batch_mean_us",
            "Batch Random Read Batch Mean Latency",
            "Batch Mean Latency (us)",
            out_dir / "batch_randread_batch_mean_latency_by_batch_size.png",
        )
        draw_batch_sweep(
            rows,
            "batch_spread_mean_us",
            "Batch Random Read Completion Spread",
            "Last - First Completion (us)",
            out_dir / "batch_randread_completion_spread_by_batch_size.png",
        )
        draw_batch_sweep(
            rows,
            "iops",
            "Batch Random Read IOPS",
            "IOPS",
            out_dir / "batch_randread_iops_by_batch_size.png",
        )


if __name__ == "__main__":
    raise SystemExit(main())
