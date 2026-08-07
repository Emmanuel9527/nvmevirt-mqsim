# NVMeVirt + MQSim Integration

## Timing Model Design

This project uses NVMeVirt as the host-facing NVMe device interface and uses
MQSim as the reference SSD model for internal timing behavior. The goal is not
to reproduce a commercial SSD with cycle-level accuracy. Instead, the timing
model should be accurate enough to compare different host/SSD architectures,
especially designs where the host and SSD repeatedly exchange data during an
ANNS query.

The main design choice is to keep the real NVMe I/O path in NVMeVirt while
moving SSD-internal timing decisions into a lightweight event-driven timing
backend. NVMeVirt should receive real NVMe commands from the Linux host, parse
their opcode, LBA, size, queue id, and command-specific metadata, and then ask
the timing backend for a simulated completion timestamp. NVMeVirt then delays
the NVMe completion until that timestamp.

MQSim should be used as the source of SSD architectural parameters and as a
validation reference, rather than as a userspace simulator that is invoked for
every small internal event. This avoids adding kernel/userspace round-trip cost
to every I/O, which would distort latency-sensitive workloads such as DiskANN
or VUC-based ANNS search. The runtime model inside NVMeVirt should therefore be
small and deterministic, while MQSim is used offline to tune and sanity-check
parameters such as NAND latency, channel count, die parallelism, queueing
behavior, and garbage collection effects.

### Responsibility Split

NVMeVirt is responsible for the real host-visible path:

- NVMe command parsing
- Submission and completion queue behavior
- Linux block layer and NVMe driver interaction
- DMA/data movement between host memory and the virtual device
- Delaying request completion according to the simulated SSD completion time
- Exposing VUCs through the real NVMe command path

The MQSim-derived timing backend is responsible for SSD-internal timing:

- FTL lookup latency
- NAND read, program, and erase latency
- NAND channel and die contention
- PCIe transfer time for host-to-device and device-to-host payloads
- SSD DRAM/cache access latency
- SSD-side compute latency for VUC or near-data processing
- Background work such as GC, if it affects foreground request timing

In the first implementation, the timing backend should not need the full MQSim
runtime in the kernel. It can use a resource reservation model, where each
shared SSD resource has a `next_available_time`:

```text
pcie_h2d.next_available_time
pcie_d2h.next_available_time
controller.next_available_time
dram.next_available_time
channel[i].next_available_time
lun[i].next_available_time
ssd_compute_unit[i].next_available_time
```

When an event uses a resource, the timing backend computes:

```text
start_time  = max(event_ready_time, resource.next_available_time)
finish_time = start_time + fixed_latency + transfer_size / bandwidth
resource.next_available_time = finish_time
```

This model is simple enough to run inside NVMeVirt, but it is still
event-driven: every NVMe request is decomposed into dependent timing events,
and each event reserves the resources it uses.

### DiskANN Query Search Example

DiskANN search is a good example because one query is not a single SSD read. A
query performs multiple rounds of dependent random reads while maintaining a
candidate list. Each round selects candidate nodes, issues I/O for those nodes,
waits for their data, computes distances, updates the candidate list, and then
decides whether the search should continue.

A simplified host-side DiskANN round is:

```text
ROUND_START
  -> SELECT_CANDIDATES
  -> ISSUE_RANDOM_READS
  -> WAIT_FOR_COMPLETIONS
  -> COMPUTE_DISTANCES
  -> UPDATE_CANDIDATE_LIST
  -> CHECK_TERMINATION
ROUND_END
```

For a host-centric DiskANN design, NVMeVirt observes the actual read requests
issued by DiskANN. Suppose a round selects `W = 8` candidate nodes. The host
issues eight asynchronous random reads:

```text
read(node_0_record)
read(node_1_record)
...
read(node_7_record)
```

Each read is converted by NVMeVirt into an SSD timing request:

```text
submit_time
queue_id
opcode = READ
lba
read_size
request_id
```

The timing backend maps each LBA to an internal SSD location, such as channel
and LUN, then computes the completion time using MQSim-style SSD timing:

```text
T_read_node =
  T_nvme_command_fetch
+ T_controller_decode
+ T_ftl_lookup
+ T_nand_random_read
+ T_channel_transfer
+ T_pcie_d2h_transfer(node_record_bytes)
+ T_completion_write
```

Because the eight reads may use different channels or LUNs, they do not always
serialize. The event-driven backend records contention by reserving each
resource. For example, if `node_0` and `node_3` map to the same NAND channel,
one of them may wait for the channel's `next_available_time`. If they map to
different channels, they may overlap.

The round completion time is determined by the slowest required I/O in that
round, plus host-side computation and candidate-list maintenance:

```text
round_io_done_time = max(
    completion_time(node_0),
    completion_time(node_1),
    ...
    completion_time(node_7)
)

round_done_time =
  round_io_done_time
+ T_host_distance_compute(returned_nodes)
+ T_candidate_list_update
```

If the host computes distances as soon as each I/O completes, then distance
computation can overlap with the remaining SSD reads. In that case, the model
should record one `IO_COMPLETE` event per node and schedule a dependent
`COMPUTE_DISTANCE` event immediately after each completion:

```text
IO_COMPLETE(node_i)
  -> COMPUTE_DISTANCE(node_i)
  -> UPDATE_CANDIDATE_LIST(node_i)
```

The next search round can start when enough candidate updates have completed
and the DiskANN termination rule decides that more candidates must be visited.

### Modeling Host/SSD Data Exchange

For this project, host/SSD data exchange must be modeled explicitly because
ANNS designs may perform many small interactions between the host and SSD. The
timing model should therefore track PCIe traffic separately from NAND and
compute time.

For every command or VUC, the model should record:

```text
host_to_ssd_bytes
ssd_to_host_bytes
pcie_h2d_start_time
pcie_h2d_finish_time
pcie_d2h_start_time
pcie_d2h_finish_time
ssd_compute_start_time
ssd_compute_finish_time
nand_read_bytes
nand_read_finish_time
completion_time
```

For a normal DiskANN read, most traffic is device-to-host because the SSD
returns node records to the host. For an SSD-assisted design, the host may send
a query vector or candidate list to the SSD, and the SSD may return only node
ids, distances, or partial top-k results. This can reduce PCIe device-to-host
traffic, but it adds SSD-side compute and possibly SSD-side state management.

For example, a VUC that asks the SSD to evaluate a batch of candidates can be
modeled as:

```text
HOST_TO_SSD_QUERY_VECTOR
  -> SSD_READ_CANDIDATE_NODE_RECORDS
  -> SSD_COMPUTE_DISTANCES
  -> SSD_UPDATE_LOCAL_CANDIDATES
  -> SSD_TO_HOST_PARTIAL_RESULTS
  -> NVME_COMPLETION
```

Its timing is:

```text
T_vuc_batch =
  T_pcie_h2d(query_vector_bytes + command_metadata)
+ T_nand_reads(candidate_node_records)
+ T_ssd_compute(num_candidates, vector_dim)
+ T_candidate_state_update
+ T_pcie_d2h(result_bytes)
+ T_completion
```

This decomposition allows us to compare different architectures by asking where
time is spent:

- host-side candidate maintenance
- host-to-SSD round trips
- PCIe data movement
- NAND random read latency and contention
- SSD-side compute
- queueing delay inside the SSD

### Metrics to Record

The simulator should report both total query latency and the breakdown of where
time was spent. For each DiskANN query, the timing trace should include:

- total query latency
- number of search rounds
- number of node reads
- reads issued per round
- average and tail SSD read latency
- host-to-SSD bytes
- SSD-to-host bytes
- NAND bytes read
- PCIe transfer time
- SSD internal queueing time
- host distance-compute time
- SSD distance-compute time
- candidate-list update time

These metrics make the result useful even if the model is not identical to a
real SSD. The important requirement is that timing differences between
architectures are explainable and based on explicit resources, rather than a
single opaque latency number.
