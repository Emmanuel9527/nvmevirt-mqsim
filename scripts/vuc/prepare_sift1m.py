#!/usr/bin/env python3
"""Pack SIFT1M into separate 4 KiB aligned neighbor and vector extents.

The output is a host-side image for NVMeVirt's memory-backed namespace. It does
not itself load the files into the reserved memory range; copy/mount the output
files there and register their extents with the existing MQSim preload path.
"""

import argparse
import json
import math
import struct
import uuid
from pathlib import Path

import numpy as np


PAGE = 4096
MAX_DEGREE = 64
RECORD_BYTES = 4 * (MAX_DEGREE + 1)
NODES_PER_NBR_PAGE = PAGE // RECORD_BYTES


def read_bin(path: Path, dtype: str):
    with path.open("rb") as f:
        header = f.read(8)
        if len(header) != 8:
            raise ValueError(f"Bad DiskANN bin header: {path}")
        count, dim = struct.unpack("<II", header)
        values = np.fromfile(f, dtype=dtype)
    if values.size != count * dim:
        raise ValueError(f"Payload size mismatch in {path}: {values.size} != {count * dim}")
    return count, dim, values.reshape(count, dim)


def read_mem_graph(path: Path, expected_nodes: int):
    """Read the variable-degree Vamana memory-index representation."""
    with path.open("rb") as f:
        raw = f.read(24)
        if len(raw) != 24:
            raise ValueError(f"Bad Vamana index header: {path}")
        file_size, width, medoid, frozen_count = struct.unpack("<QIIQ", raw)
        f.seek(0, 2)
        if f.tell() != file_size:
            raise ValueError(f"Vamana size mismatch: header {file_size}, file {f.tell()}")
        f.seek(24)
        graph = []
        for node_id in range(expected_nodes):
            raw_degree = f.read(4)
            if len(raw_degree) != 4:
                raise ValueError(f"Truncated degree for node {node_id}")
            degree = struct.unpack("<I", raw_degree)[0]
            if degree > width or degree > MAX_DEGREE:
                raise ValueError(f"Node {node_id} degree {degree} exceeds max {MAX_DEGREE}")
            raw_neighbors = f.read(degree * 4)
            if len(raw_neighbors) != degree * 4:
                raise ValueError(f"Truncated neighbor list for node {node_id}")
            neighbors = np.frombuffer(raw_neighbors, dtype="<u4").copy()
            if np.any(neighbors >= expected_nodes):
                raise ValueError(f"Out-of-range neighbor ID at node {node_id}")
            graph.append(neighbors)
        if f.read(1):
            raise ValueError("Unexpected trailing bytes in Vamana memory index")
    return graph, width, medoid, frozen_count


def read_u32_map(path: Path, n: int):
    count, dim, values = read_bin(path, "<u4")
    if count != n or dim != 1:
        raise ValueError(f"Expected a {n}-entry 1D map in {path}")
    values = values[:, 0]
    if not np.array_equal(np.sort(values), np.arange(n, dtype=np.uint32)):
        raise ValueError(f"Map is not a permutation: {path}")
    return values


def write_page_header(f, magic: bytes, version: int, n: int, dim: int, degree: int = 0):
    header = struct.pack("<8sIIII", magic, version, n, dim, degree)
    f.write(header)
    f.write(bytes(PAGE - len(header)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True, help="SIFT1M base .fbin")
    p.add_argument("--mem-index", type=Path, required=True, help="DiskANN Vamana .mem.index")
    p.add_argument("--pq-codes", type=Path, required=True, help="DiskANN PQ compressed .bin")
    p.add_argument("--pq-pivots", type=Path, required=True, help="DiskANN PQ pivots .bin")
    p.add_argument("--nbr-old-to-new-map", type=Path,
                   help="Optional NBR-only placement map; identity order is used if omitted")
    p.add_argument("--vector-old-to-new-map", type=Path, help="Independent vector placement permutation")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    n, dim, vectors = read_bin(args.base, "<f4")
    graph, width, medoid, frozen_count = read_mem_graph(args.mem_index, n)
    if dim != 128 or width > MAX_DEGREE:
        raise ValueError(f"Unexpected SIFT1M shape: n={n}, dim={dim}, graph width={width}")

    nbr_old_to_new = (read_u32_map(args.nbr_old_to_new_map, n)
                      if args.nbr_old_to_new_map else np.arange(n, dtype=np.uint32))
    slot_to_node = np.empty(n, dtype=np.uint32)
    slot_to_node[nbr_old_to_new] = np.arange(n, dtype=np.uint32)
    node_to_nbr_slot = nbr_old_to_new

    args.out_dir.mkdir(parents=True, exist_ok=True)
    nbr_path = args.out_dir / "sift1m.nbr4k"
    with nbr_path.open("wb") as f:
        write_page_header(f, b"NBRONLY1", 1, n, dim, width)
        for page_start in range(0, n, NODES_PER_NBR_PAGE):
            page = bytearray(PAGE)
            for slot in range(NODES_PER_NBR_PAGE):
                physical_slot = page_start + slot
                if physical_slot >= n:
                    break
                node_id = int(slot_to_node[physical_slot])
                nbrs = graph[node_id]
                off = slot * RECORD_BYTES
                struct.pack_into("<I", page, off, len(nbrs))
                if len(nbrs):
                    struct.pack_into("<" + "I" * len(nbrs), page, off + 4,
                                     *(int(x) for x in nbrs))
            f.write(page)

    vector_map = (read_u32_map(args.vector_old_to_new_map, n)
                  if args.vector_old_to_new_map else np.arange(n, dtype=np.uint32))
    placed_vectors = np.empty_like(vectors)
    placed_vectors[vector_map] = vectors
    vectors_path = args.out_dir / "sift1m.vectors4k"
    with vectors_path.open("wb") as f:
        write_page_header(f, b"VECF32V1", 1, n, dim)
        f.write(placed_vectors.astype("<f4", copy=False).tobytes(order="C"))
        f.write(bytes((-n * dim * 4) % PAGE))

    # Keep DiskANN's trained PQ table/code format. Reorder codes only if the
    # NBR placement map changes IDs; this keeps Host PQ lookup keyed by node ID.
    code_n, code_dim, codes = read_bin(args.pq_codes, "u1")
    if code_n != n:
        raise ValueError(f"PQ code count mismatch: {code_n} != {n}")
    host_codes = np.empty_like(codes)
    host_codes[nbr_old_to_new] = codes
    codes_out = args.out_dir / "sift1m.pq_codes.bin"
    with codes_out.open("wb") as f:
        f.write(struct.pack("<II", n, code_dim))
        f.write(host_codes.tobytes(order="C"))
    pivots_out = args.out_dir / "sift1m.pq_pivots.bin"
    pivots_out.write_bytes(args.pq_pivots.read_bytes())

    node_map_path = args.out_dir / "sift1m.node_to_nbr_slot.u32"
    with node_map_path.open("wb") as f:
        f.write(struct.pack("<II", n, 1))
        f.write(node_to_nbr_slot.astype("<u4", copy=False).tobytes())

    vector_map_path = args.out_dir / "sift1m.node_to_vector_slot.u32"
    with vector_map_path.open("wb") as f:
        f.write(struct.pack("<II", n, 1))
        f.write(vector_map.astype("<u4", copy=False).tobytes())

    metadata = {
        "format_version": 2,
        "index_id": str(uuid.uuid4()),
        "dataset": "SIFT1M",
        "nodes": n,
        "dimension": dim,
        "distance": "squared_l2_fp32",
        "graph_width": width,
        "medoid_node_id": medoid,
        "frozen_count": frozen_count,
        "page_bytes": PAGE,
        "neighbor_record_bytes": RECORD_BYTES,
        "nodes_per_neighbor_page": NODES_PER_NBR_PAGE,
        "neighbor_header_pages": 1,
        "vector_bytes_per_node": dim * 4,
        "vectors_per_page": PAGE // (dim * 4),
        "vector_header_pages": 1,
        "neighbor_pages": 1 + math.ceil(n / NODES_PER_NBR_PAGE),
        "vector_pages": 1 + math.ceil(n * dim * 4 / PAGE),
        "neighbor_map": node_map_path.name,
        "vector_map": vector_map_path.name,
        "vector_source_map": str(args.vector_old_to_new_map) if args.vector_old_to_new_map else "identity",
        "source_map": str(args.nbr_old_to_new_map) if args.nbr_old_to_new_map else "identity",
    }
    (args.out_dir / "sift1m.layout.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
