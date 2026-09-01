#!/usr/bin/env python3
import argparse
import collections
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_lines(lines):
    sizes_by_action = collections.defaultdict(collections.Counter)
    comm_by_action = collections.defaultdict(collections.Counter)
    flag_by_action = collections.defaultdict(collections.Counter)

    for line in lines:
        parts = line.split()
        if len(parts) < 11:
            continue

        action = parts[5]
        rw_flags = parts[6]
        if "R" not in rw_flags:
            continue

        try:
            plus_idx = parts.index("+")
            sectors = int(parts[plus_idx + 1])
        except (ValueError, IndexError):
            continue

        bytes_len = sectors * 512
        sizes_by_action[action][bytes_len] += 1
        flag_by_action[action][rw_flags] += 1

        match = re.search(r"\[([^\]]*)\]\s*$", line)
        comm = match.group(1) if match else "unknown"
        comm_by_action[action][comm] += 1

    return sizes_by_action, comm_by_action, flag_by_action


def write_size_csv(path, run_label, sizes_by_action):
    with open(path, "w") as f:
        f.write("run_label,action,bytes,count\n")
        for action in sorted(sizes_by_action):
            for bytes_len, count in sorted(sizes_by_action[action].items()):
                f.write(f"{run_label},{action},{bytes_len},{count}\n")


def write_comm_csv(path, run_label, comm_by_action):
    with open(path, "w") as f:
        f.write("run_label,action,comm,count\n")
        for action in sorted(comm_by_action):
            for comm, count in comm_by_action[action].most_common():
                f.write(f"{run_label},{action},{comm},{count}\n")


def write_flag_csv(path, run_label, flag_by_action):
    with open(path, "w") as f:
        f.write("run_label,action,rw_flags,count\n")
        for action in sorted(flag_by_action):
            for flags, count in flag_by_action[action].most_common():
                f.write(f"{run_label},{action},{flags},{count}\n")


def plot_size_distribution(path, run_label, sizes_by_action):
    actions = [a for a in ["Q", "D", "C"] if sizes_by_action.get(a)]
    if not actions:
        return

    all_sizes = sorted(set().union(*[set(sizes_by_action[a].keys()) for a in actions]))
    labels = [f"{size // 1024}K" if size >= 1024 else str(size) for size in all_sizes]
    x = range(len(all_sizes))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    offsets = {"Q": -width, "D": 0, "C": width}
    colors = {"Q": "#3867d6", "D": "#20bf6b", "C": "#eb3b5a"}
    for action in actions:
        counts = [sizes_by_action[action].get(size, 0) for size in all_sizes]
        ax.bar([i + offsets.get(action, 0) for i in x], counts, width, label=action, color=colors.get(action))

    ax.set_title(f"{run_label} read request size distribution")
    ax.set_xlabel("Request size")
    ax.set_ylabel("Count")
    ax.set_yscale("log")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(True, axis="y", which="both", alpha=0.3)
    ax.legend(title="blk action")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_comm_distribution(path, run_label, comm_by_action):
    q_counts = comm_by_action.get("Q", collections.Counter())
    if not q_counts:
        return

    top = q_counts.most_common(12)
    labels = [item[0] for item in top]
    counts = [item[1] for item in top]

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    ax.bar(labels, counts, color="#8854d0")
    ax.set_title(f"{run_label} top read queue submitters")
    ax.set_xlabel("comm from Q events")
    ax.set_ylabel("Count")
    ax.set_yscale("log")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, axis="y", which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sizes_by_action, comm_by_action, flag_by_action = parse_lines(iter(input, ""))

    write_size_csv(output_dir / f"{args.run_label}.read_size_distribution.csv", args.run_label, sizes_by_action)
    write_comm_csv(output_dir / f"{args.run_label}.read_comm_distribution.csv", args.run_label, comm_by_action)
    write_flag_csv(output_dir / f"{args.run_label}.read_flag_distribution.csv", args.run_label, flag_by_action)
    plot_size_distribution(output_dir / f"{args.run_label}.read_size_distribution.png", args.run_label, sizes_by_action)
    plot_comm_distribution(output_dir / f"{args.run_label}.read_comm_distribution.png", args.run_label, comm_by_action)

    print(output_dir / f"{args.run_label}.read_size_distribution.csv")
    print(output_dir / f"{args.run_label}.read_comm_distribution.csv")
    print(output_dir / f"{args.run_label}.read_size_distribution.png")
    print(output_dir / f"{args.run_label}.read_comm_distribution.png")


if __name__ == "__main__":
    main()
