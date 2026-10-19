#!/usr/bin/env python3
"""Integration test: real MQSim, tiny page images, stage trace invariants."""
import csv
from pathlib import Path
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]

def header(magic, degree):
    return struct.pack('<8sIIII', magic, 1, 32, 128, degree).ljust(4096, b'\0')

with tempfile.TemporaryDirectory(prefix='vuc-timing-') as directory:
    root = Path(directory)
    nbr = bytearray(header(b'NBRONLY1', 64) + bytes(3 * 4096))
    for i in range(32):
        struct.pack_into('<II', nbr, 4096 + (i // 15) * 4096 + (i % 15) * 260, 1, (i + 1) % 32)
    (root / 'nbr').write_bytes(nbr)
    (root / 'vec').write_bytes(header(b'VECF32V1', 0) + b''.join(struct.pack('<128f', *([float(i)] * 128)) for i in reversed(range(32))))
    (root / 'vec_map').write_bytes(struct.pack('<II32I', 32, 1, *reversed(range(32))))
    (root / 'map').write_bytes(struct.pack('<II32I', 32, 1, *range(32)))
    for name, pages, start in [('nbr_lba', 4, 0), ('vec_lba', 5, 64)]:
        (root / name).write_bytes(struct.pack('<II', pages, 1) + struct.pack('<' + 'Q' * pages, *(start + p * 8 for p in range(pages))))
    tree = ET.parse(ROOT / 'mqsim/ssdconfig.xml')
    for tag, value in [('Flash_Channel_Count', 2), ('Chip_No_Per_Channel', 2), ('Block_No_Per_Plane', 32), ('Page_No_Per_Block', 64), ('Data_Cache_Capacity', 1048576)]:
        tree.find('.//' + tag).text = str(value)
    tree.write(root / 'ssd.xml')
    subprocess.run([str(ROOT / 'mqsim/VUCTimingSmoke'), str(root)], check=True)
    rows = list(csv.DictReader((root / 'trace.csv').open()))
    for mode in range(4):
        group = [r for r in rows if int(r['query_id']) == mode]
        dma = sorted((r for r in group if r['stage'] in ('dbuf_to_dlm', 'dlm_to_dbuf', 'query_to_dlm')), key=lambda r: int(r['start_ns']))
        assert len(dma) == 9
        for a, b in zip(dma, dma[1:]):
            assert int(a['finish_ns']) <= int(b['start_ns']), 'shared DMA overlapped'
        for page in range(1, 5):
            stages = {r['stage']: r for r in group if r['kind'] == 'vector' and int(r['page']) == page}
            order = ['internal_read', 'dbuf_to_dlm', 'dsp', 'dlm_to_dbuf', 'candidate_update']
            for a, b in zip(order, order[1:]):
                assert int(stages[a]['finish_ns']) <= int(stages[b]['start_ns']), 'dependency violation'
        if mode == 1:
            reads = sorted((r for r in group if r['stage'] == 'internal_read'), key=lambda r: int(r['start_ns']))
            for a, b in zip(reads, reads[1:]):
                assert int(a['finish_ns']) <= int(b['start_ns']), 'one-slot DBUF overcommitted'
    summary = subprocess.run(['python3', str(ROOT / 'scripts/vuc/summarize_timing_trace.py'), str(root / 'trace.csv')], check=True, capture_output=True, text=True)
    assert len(list(csv.DictReader(summary.stdout.splitlines()))) == 6
    print('PASS: nonzero/zero costs, tiny buffers, exact results, DMA serialization and stage dependencies')
