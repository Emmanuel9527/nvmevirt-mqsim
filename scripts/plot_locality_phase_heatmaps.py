#!/usr/bin/env python3
"""Plot phase-binned sector-reuse metrics for SIFT1M and SIFT100M."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PHASES = ["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"]
METRICS = [
    ("batches_with_shared_sector_pct", "Batches with a shared sector (%)", 65),
    ("node_reads_in_shared_sectors_pct", "Node reads in shared sectors (%)", 12),
    ("duplicate_sector_request_ratio_pct", "Duplicate sector requests, (N−U)/N (%)", 6),
]


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def plot_dataset(csv_path, dataset, output_path):
    rows = load_rows(csv_path)
    configs = sorted({(int(row["L"]), int(row["W"])) for row in rows})
    config_labels = [f"L={L}, W={W}" for L, W in configs]
    phase_keys = [f"{i * 20}-{(i + 1) * 20}%" for i in range(5)]

    fig, axes = plt.subplots(1, 3, figsize=(15, 8.5), constrained_layout=True)
    cmap = plt.get_cmap("YlOrRd")
    for ax, (field, title, vmax) in zip(axes, METRICS):
        matrix = np.full((len(configs), len(phase_keys)), np.nan)
        lookup = {(int(r["L"]), int(r["W"]), r["progress_range"]): float(r[field]) for r in rows}
        for y, (L, W) in enumerate(configs):
            for x, phase in enumerate(phase_keys):
                matrix[y, x] = lookup[(L, W, phase)]

        image = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
        ax.set_title(title, fontsize=10, pad=10)
        ax.set_xticks(range(len(PHASES)), PHASES, rotation=35, ha="right")
        ax.set_yticks(range(len(config_labels)), config_labels)
        ax.set_xlabel("Search progress within each query")
        ax.tick_params(axis="y", labelsize=8)
        ax.set_xticks(np.arange(-0.5, len(PHASES), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(configs), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.2)
        ax.tick_params(which="minor", bottom=False, left=False)

        threshold = vmax * 0.57
        for y in range(matrix.shape[0]):
            for x in range(matrix.shape[1]):
                value = matrix[y, x]
                color = "white" if value >= threshold else "#222222"
                ax.text(x, y, f"{value:.1f}", ha="center", va="center", fontsize=7.5, color=color)

        colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.03)
        colorbar.ax.tick_params(labelsize=8)

    fig.suptitle(f"{dataset}: sector reuse by search progress", fontsize=14)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {output_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input_dir", default="results/locality_phase_20261013")
    parser.add_argument(
        "--output_dir",
        default="/home/emmanuel/projects/DiskANN_cpp/results/locality_phase_heatmaps_20261013",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    for dataset in ("sift1m", "sift100m"):
        plot_dataset(
            input_dir / f"{dataset}_sector_reuse_by_lifecycle.csv",
            dataset.upper(),
            output_dir / f"{dataset}_sector_reuse_heatmap.png",
        )


if __name__ == "__main__":
    main()
