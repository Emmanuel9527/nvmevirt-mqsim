#!/usr/bin/env python3
"""Summarize observed VUC internal-read traces, not a standalone random-read benchmark."""
import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('trace')
a = p.parse_args()
groups = defaultdict(list)
with open(a.trace, newline='') as f:
    for row in csv.DictReader(f):
        if row['stage'] == 'internal_read':
            groups[(row['query_id'], row['batch_id'])].append(row)
writer = csv.writer(sys.stdout)
writer.writerow(['query_id', 'batch_id', 'reads', 'read_window_ns', 'observed_IOPS',
                 'observed_MB_per_s', 'average_ns', 'p50_ns', 'p95_ns', 'p99_ns'])
for (qid, bid), rows in groups.items():
    latency = sorted(int(r['finish_ns']) - int(r['start_ns']) for r in rows)
    duration = max(int(r['finish_ns']) for r in rows) - min(int(r['start_ns']) for r in rows)
    quantile = lambda p: latency[max(0, math.ceil(p * len(latency)) - 1)]
    writer.writerow([qid, bid, len(rows), duration, len(rows)*1e9/duration if duration else 0,
                     sum(int(r['bytes']) for r in rows)*1e3/duration if duration else 0,
                     statistics.mean(latency), quantile(.5), quantile(.95), quantile(.99)])
