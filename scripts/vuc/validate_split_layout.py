#!/usr/bin/env python3
"""Validate independent permutations and sampled original graph/vector/PQ identities."""
import argparse
import json
from pathlib import Path
import struct
import numpy as np
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--layout',type=Path,required=True)
p.add_argument('--base',type=Path,required=True)
p.add_argument('--mem-index',type=Path,required=True)
p.add_argument('--pq-codes',type=Path,required=True)
a=p.parse_args()
m=json.loads(a.layout.read_text()); root=a.layout.parent; n=m['nodes']
def matrix(path,dtype):
    with open(path,'rb') as f: rows,cols=struct.unpack('<II',f.read(8))
    return np.memmap(path,dtype=dtype,mode='r',offset=8,shape=(rows,cols))
nbrmap=matrix(root/m['neighbor_map'],'<u4')[:,0]
vecmap=matrix(root/m['vector_map'],'<u4')[:,0]
for mapping in (nbrmap,vecmap):
    assert np.array_equal(np.sort(mapping),np.arange(n,dtype=np.uint32)), 'not a permutation'
base=matrix(a.base,'<f4'); codes=matrix(a.pq_codes,'u1'); placed_codes=matrix(root/'sift1m.pq_codes.bin','u1')
nbr=np.memmap(root/'sift1m.nbr4k',dtype='u1',mode='r')
vec=np.memmap(root/'sift1m.vectors4k',dtype='u1',mode='r')
selected=set(np.random.default_rng(42).choice(n,min(n,1000),replace=False).tolist()) | {0,n-1,m['medoid_node_id']}
with a.mem_index.open('rb') as f:
    f.seek(24)
    for node in range(n):
        degree,=struct.unpack('<I',f.read(4)); ids=f.read(degree*4)
        if node not in selected: continue
        ns=int(nbrmap[node]); vs=int(vecmap[node])
        offset=4096+(ns//15)*4096+(ns%15)*260
        assert bytes(nbr[offset:offset+4+degree*4]) == struct.pack('<I',degree)+ids, 'adjacency identity changed'
        assert bytes(vec[4096+vs*512:4096+(vs+1)*512]) == base[node].tobytes(), 'vector identity changed'
        assert np.array_equal(placed_codes[ns],codes[node]), 'PQ identity changed'
print(f'PASS: two permutations; {len(selected)} sampled logical nodes retain adjacency, vector and PQ identity')
