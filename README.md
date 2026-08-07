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

## SSD 內部元件與 NAND Flash 結構

本章整理 SSD 內部主要元件，以及 NAND flash 在 datasheet 中呈現的階層結構。這份專案目前參考的 datasheet 是：

```text
NAND_data_sheet/MX35LF4G24AD, 3V, 4Gb, v1.4.pdf
```

這份 datasheet 描述的是 Macronix `MX35LFxG24AD` 系列 Serial NAND Flash memory。它是一顆 NAND flash chip，不是一整顆 SSD。因此閱讀時要先分清楚兩個層級：

- **NAND flash chip 層級**：datasheet 主要描述的對象，例如 page、block、plane、cache register、serial interface、read/program/erase timing。
- **SSD system 層級**：SSD controller 把多顆 NAND flash chip、channel、DRAM、FTL、NVMe interface 組合起來後形成的完整裝置。

在我們的 NVMeVirt + MQSim 模擬器中，NVMeVirt 會扮演 host 看到的 NVMe SSD，而 MQSim 或 MQSim-derived timing model 會負責描述 SSD 內部的 NAND hierarchy、parallelism、queueing、FTL 與 timing。

### 整體 SSD 階層

一顆 SSD 可以粗略看成以下階層：

```text
Host
  -> PCIe / NVMe interface
  -> SSD controller
      -> firmware / FTL
      -> DRAM / SRAM buffer
      -> NAND channels
          -> NAND package / chip
              -> die / LUN
                  -> plane
                      -> block
                          -> page
                              -> main data area
                              -> spare / OOB area
```

這個階層對 timing model 很重要，因為不同層級代表不同種類的資源競爭：

- PCIe link 會影響 host 與 SSD 之間的資料傳輸時間。
- SSD controller 會影響 command decode、FTL lookup、queue scheduling、VUC processing。
- NAND channel 會影響多個 NAND chip/die 是否能同時傳資料。
- die 或 LUN 會影響 NAND array operation 是否能平行。
- plane 會影響 multi-plane operation 與 address mapping。
- block 是 erase 的基本單位。
- page 是 read/program 的基本單位。

### Host Interface：PCIe 與 NVMe

Host 不會直接對 NAND flash 下 `PAGE READ` 或 `PROGRAM EXECUTE` 這類低階命令。Host 看到的是 NVMe SSD，通常透過 PCIe 傳送 NVMe command：

```text
NVMe read
NVMe write
flush
admin command
vendor unique command, VUC
```

NVMe command 到達 SSD 後，SSD controller 會把 host-level request 轉成內部 NAND operation。例如一個 NVMe read 可能會變成：

```text
NVMe READ
  -> parse command
  -> FTL lookup: LBA -> physical page address
  -> NAND PAGE READ
  -> read from cache/register
  -> DMA data back to host
  -> NVMe completion
```

在我們的模擬器中，這一層由 NVMeVirt 負責。NVMeVirt 的價值是讓實驗真的走 Linux NVMe I/O path，而不是只在 userspace 產生抽象 request。

### SSD Controller

SSD controller 是 SSD 內部最重要的控制中心。它通常負責：

- 接收與解析 NVMe command
- 管理 submission queue 和 completion queue
- 做 DMA，把資料在 host memory 和 SSD buffer 之間搬移
- 執行 firmware
- 維護 FTL mapping table
- 安排 NAND read/program/erase
- 管理 garbage collection
- 做 wear leveling
- 做 bad block management
- 執行 ECC encode/decode
- 控制 NAND channel 和 die-level parallelism
- 處理 VUC 或 near-data processing command

對我們的研究來說，controller timing 不能只是一個固定常數。尤其 DiskANN/ANNS 會大量發小 I/O 或 VUC，controller 可能會花時間在：

- command decode
- candidate metadata parsing
- query vector copy
- SSD-side distance computation
- candidate list update
- scheduling NAND reads
- preparing result buffer

因此 timing model 應該至少把 controller 拆成幾個資源：

```text
controller_frontend
ftl_engine
dram_or_sram
ssd_compute_unit
completion_engine
```

這樣才可以比較不同架構下，時間是花在 NAND、PCIe、host compute，還是 SSD controller compute。

### FTL：Flash Translation Layer

FTL 是 SSD firmware 中負責地址轉換與 flash 管理的核心。Host 發出的地址是 LBA，NAND 內部真正使用的是 physical page/block address。

FTL 通常需要處理：

- LBA 到 physical page 的 mapping
- out-of-place update
- invalid page tracking
- garbage collection
- wear leveling
- bad block avoidance
- write amplification
- metadata persistence

NAND flash 的重要限制是：

- read 的基本單位是 page
- program 的基本單位是 page
- erase 的基本單位是 block
- page program 通常要求同一個 block 內由低 page address 往高 page address 寫
- 已經 program 過的 page 不能像 DRAM 那樣直接覆寫，通常要寫到新 page，舊 page 標成 invalid

所以 SSD write latency 不只是 page program time。當空間變少或 invalid pages 累積時，GC 可能需要：

```text
read valid pages from old block
program valid pages to new block
erase old block
update mapping table
```

這也是 MQSim 對我們有價值的地方：MQSim 的 FTL/GC 模型可以幫助我們校正 NVMeVirt 內部 timing backend，不讓 write 和 GC 的行為過度簡化。

### NAND Channel

Channel 是 SSD controller 與 NAND chips 之間的資料通道。多 channel 是 SSD internal parallelism 的主要來源之一。

概念上可以想成：

```text
controller
  -> channel 0 -> NAND chips
  -> channel 1 -> NAND chips
  -> channel 2 -> NAND chips
  -> channel 3 -> NAND chips
```

如果兩個 read 被分配到不同 channel，它們的資料傳輸可以重疊。如果它們落在同一個 channel，就會競爭 channel bandwidth 或 command/data bus。

對 DiskANN 這種大量 random read workload 來說，LBA-to-channel mapping 很重要。假設一輪 search 發出 8 個 candidate node reads：

```text
node_0 -> channel 0
node_1 -> channel 3
node_2 -> channel 1
node_3 -> channel 0
...
```

`node_0` 和 `node_3` 如果落在同一個 channel，就可能互相排隊；落在不同 channel 則可以平行完成。這會直接影響一輪 search 的 tail latency。

### NAND Package / Chip

一個 NAND package 是實體封裝。在商用 SSD 中，一個 package 裡面可能包含多個 die；但本 datasheet 描述的 `MX35LF4G24AD` 可視為一顆 serial NAND memory device。

這顆 device 的關鍵特性包括：

- 3V Serial NAND Flash
- SLC NAND
- x4 I/O support
- 4Gb density 版本可提供 4Gbit raw density，也就是約 512MiB main data capacity
- 4Gb 版本 page size 是 `(4096 + 256)` bytes
- 4Gb 版本 block size 是 `(256K + 16K)` bytes
- 4Gb/2Gb 為 two-plane structure
- operating temperature 為 -40C 到 85C
- 典型 program/erase endurance 為 60K cycles
- 需要 host-side 8-bit ECC per 544 bytes

注意這顆是 Serial NAND，因此 datasheet 中會看到 `CS#`、`SCLK`、`SI/SIO0`、`SO/SIO1`、`WP#/SIO2`、`HOLD#/SIO3` 等 SPI-like pins。這和 NVMe SSD 內部常見的 parallel NAND / ONFI interface 不完全相同，但 page/block/plane/read/program/erase 的概念仍然很適合用來理解 NAND flash 基本結構。

### Die 與 LUN

在 SSD 模型中，die 或 LUN 通常是 NAND 內部可以獨立執行 array operation 的單位。很多 SSD simulator 會把 LUN 視為一個可排程資源：

```text
lun.next_available_time
```

如果兩個 NAND operation 需要同一個 LUN，它們通常不能完全同時執行；如果它們在不同 LUN，則可能平行。

在這份 datasheet 的 parameter page 中，`MX35LF4G24AD` 的 `Number of Logical Units` 是 `1`。因此針對單顆 MX35LF4G24AD，可以先把它建成：

```text
1 package/chip
  -> 1 LUN
      -> 2 planes
          -> blocks
              -> pages
```

不過在完整 SSD 中，controller 會接多顆 NAND chip。MQSim 裡的 `LUN`、`chip`、`die`、`channel` 設定應該反映整個 SSD，而不是只反映一顆 NAND chip。

### Plane

Plane 是 die/LUN 內部更低一層的 array partition。Plane 的存在讓 NAND 有機會做 multi-plane operation，也會影響 address mapping。

Datasheet 特別提到：

- 1Gb 是 physical 1-plane structure
- 2Gb/4Gb 是 two-plane structure
- 某些 2Gb/4Gb part number 需要在 column address 中提供 plane select bit
- 對 `MX35LF4G24AD-Z4I`，4Gb 的 plane select bit 是 `RA[6]`
- `RA[6]` 對 even blocks 必須為 `0`，對 odd blocks 必須為 `1`
- `MX35LF4G24AD-Z4I8` 則不需要 column address plane select bit

這代表 plane 不只是容量切分，也會出現在 address encoding 和 program/load command 的格式中。

在模擬器裡，plane 可以先用兩種方式建模：

```text
簡化模型：
  plane 只影響 address mapping，不提供額外 parallelism。

較完整模型：
  plane 可以支援 multi-plane read/program，但需要檢查 command/address 限制。
```

第一階段若重點是 DiskANN read timing，可以先把 plane 視為 address mapping 的一部分；等需要比較 internal parallelism 時，再加入 multi-plane timing。

### Block

Block 是 NAND erase 的基本單位。對 4Gb 版本而言：

```text
page size  = 4096 + 256 bytes
pages/block = 64
block size = 256KiB + 16KiB
blocks/unit = 2048
```

這裡的 `4096 bytes` 是 main data area，`256 bytes` 是 spare/OOB area。64 個 page 組成一個 block，所以 main data area 是：

```text
4096 bytes/page * 64 pages = 262144 bytes = 256KiB
```

spare area 則是：

```text
256 bytes/page * 64 pages = 16384 bytes = 16KiB
```

Block erase 的 timing 由 `tERASE` 描述。Datasheet 中 block erase typical 是 `4 ms`，maximum 是 `6 ms`。

在 SSD 裡，block 很重要，因為：

- erase 只能以 block 為單位
- GC 會挑 victim block
- wear leveling 會根據 block erase count 做決策
- bad block management 也是 block 粒度
- write amplification 和 block valid page count 有關

NVMeVirt/MQSim 的 FTL 如果要模擬 write-heavy workload，就需要至少追蹤：

```text
block.valid_page_count
block.invalid_page_count
block.erase_count
block.is_bad
block.write_pointer
```

### Page

Page 是 NAND read 和 program 的基本單位。對 `MX35LF4G24AD`：

```text
main data per page  = 4096 bytes
spare bytes per page = 256 bytes
total bytes per page = 4352 bytes
```

Datasheet 也列出 partial page：

```text
partial page main data = 1024 bytes
partial page spare = 64 bytes
number of programs per page = 4
```

這代表同一個 page 最多允許 4 次 partial programming。對 SSD 模擬來說，第一版通常不需要細到 partial programming；可以把 4KiB page 視為最小 mapping/read/program 單位。這剛好也和許多 SSD simulator 中的 4KiB logical page 對齊。

Page read 在 datasheet 中分成兩個階段：

```text
PAGE READ (13h): array -> internal cache/register
READ FROM CACHE: internal cache/register -> host/controller
```

這對 timing model 很重要，因為 NAND read 不是只有一個動作。它包含：

```text
array sensing time
cache/register transfer
I/O bus transfer
```

Datasheet 給的 array-to-register read latency 是 `tRD = 25 us`。資料真正從 cache/register 讀出來，還要受 serial clock frequency 和 I/O width 影響。

### Spare / OOB Area

每個 NAND page 除了 main data area，還有 spare area，也常被稱為 OOB area。對 4Gb 版本：

```text
main data area = 4096 bytes
spare/OOB area = 256 bytes
```

Spare area 通常用來存：

- ECC parity
- bad block marker
- logical/page metadata
- FTL metadata
- wear-leveling 或 internal bookkeeping information

Datasheet 指出 good block 出廠時 data bytes 皆為 `FFh`；bad block 的標記會放在 spare area 的特定位置，尤其是第 1 和第 2 page 的 spare area 第 1 byte 可能為 `00h`。因此系統軟體應該在 erase 前讀出 bad block information，建立 bad block table，避免誤用 bad block。

對我們的模擬器來說，spare area 不一定要真的儲存完整 bytes，但 timing/FTL model 至少要理解：

```text
page main data bytes
page spare bytes
ECC requirement
bad block marker
metadata overhead
```

### Cache Register / Page Buffer

Serial NAND read 不是直接從 NAND array 一個 byte 一個 byte 送到 host。常見流程是：

```text
1. PAGE READ (13h)
   NAND array -> internal cache/register

2. READ FROM CACHE (03h/0Bh/3Bh/6Bh/BBh/EBh)
   internal cache/register -> external interface
```

這個 cache/register 很像 NAND chip 內部的 page buffer。它讓 array sensing 和外部資料輸出分成兩個階段。

Datasheet 也支援 cache read：

```text
PAGE READ CACHE RANDOM (30h)
PAGE READ CACHE SEQUENTIAL (31h)
PAGE READ CACHE END (3Fh)
```

Cache read 的目的是提升連續或 pipeline read 的 throughput：當上一頁資料正在從 cache/register 輸出時，下一頁可以被讀進 cache/register。Datasheet 中提到 cache read 可以把 page 間的等待從 `tRD` 降到 `tRCBSY`，而 `tRCBSY(Read)` typical 是 `4.5 us`，maximum 是 `25 us`。

對 DiskANN 這類 random read workload，cache sequential read 不一定有明顯幫助，因為 node access 多半不連續。但如果 DiskANN node layout 經過設計，讓 neighbor list 或相鄰 candidate nodes 落在連續 page，就可能讓 cache read 或 read-ahead 有價值。

### NAND Read / Program / Erase Timing

這份 datasheet 中幾個對模擬最重要的 timing 是：

```text
tRD:
  array -> cache/register read time
  max 25 us

tPROG:
  page program time, randomizer disabled
  typ 320 us, max 700 us

tPROG_RAND:
  page program time, randomizer enabled
  typ 360 us, max 740 us

tRCBSY(Read):
  cache read dummy busy time
  typ 4.5 us, max 25 us

tERASE:
  block erase time
  typ 4 ms, max 6 ms
```

因此，在 timing model 中，read/program/erase 不應該只有 bandwidth 公式。至少要有：

```text
read:
  NAND array sensing latency + data transfer latency

program:
  data load latency + page program latency

erase:
  block erase latency
```

對 host 看到的 NVMe read，完整 timing 可以拆成：

```text
T_nvme_read =
  T_command_fetch
+ T_controller_decode
+ T_ftl_lookup
+ T_nand_tRD
+ T_nand_cache_to_controller_transfer
+ T_pcie_d2h_dma
+ T_completion
```

對 NVMe write：

```text
T_nvme_write =
  T_command_fetch
+ T_pcie_h2d_dma
+ T_write_buffer
+ T_ftl_update
+ T_nand_program_load
+ T_nand_tPROG
+ T_completion_policy
```

如果 SSD 使用 early completion，host 可能在資料進入 SSD buffer 後就收到 completion，而不是等 NAND program 完成。這種情況必須在模型中明確表示，否則 write latency 會被高估或低估。

### ECC

Datasheet 指出這顆 NAND 需要 host-side `8-bit ECC / 544-byte` operation。這表示 raw NAND 本身不能假設每次 read 都可靠，系統需要 ECC 來修正 bit errors。

在真實 SSD 中，ECC 通常由 SSD controller 負責，不會交給 OS 或 application。這份 Serial NAND datasheet 寫 host-side ECC，是因為它描述的是裸 NAND device，使用者通常是 microcontroller 或 embedded system。

對我們的模擬器，ECC 可以分三個層次處理：

```text
第一階段：
  不模擬 bit error，只加入固定 ECC decode latency。

第二階段：
  根據 read count / erase count 加入可校正錯誤率，影響 ECC latency。

第三階段：
  模擬 uncorrectable error、read retry、special read for data recovery。
```

目前若研究重點是 ANNS 架構速度，第一階段加入固定 ECC latency 就足夠。

### Bad Block

NAND flash 出廠時就可能有 bad blocks，使用過程中也可能產生新的 bad blocks。Datasheet 對 4Gb 版本列出：

```text
total blocks = 2048
minimum valid good blocks = 2008
block 0-7 guaranteed good at shipment
```

Bad block 的重點是：

- bad block 不應該被 erase/program 使用
- 系統應建立 bad block table
- 如果 erase/program failure 發生，通常需要 block replacement
- read failure 則依靠 ECC 或 read retry/special read 處理

在 SSD simulator 裡，bad block 不一定要第一版就做得很細。但容量計算與 over-provisioning 不能假設所有 block 都永遠可用。至少應該把 good block count 和 reserved blocks 的概念放進 config。

### Mapping 到 NVMeVirt 與 MQSim

從 datasheet 角度看，NAND chip 的基本參數可以轉成 MQSim/NVMeVirt timing model 的 config：

```text
page_main_size = 4096 bytes
page_spare_size = 256 bytes
pages_per_block = 64
blocks_per_lun = 2048
luns_per_chip = 1
planes_per_lun = 2
bits_per_cell = 1
t_read = 25 us
t_program = 320 us typical, 700 us max
t_erase = 4 ms typical, 6 ms max
ecc_strength = 8-bit per 544 bytes
```

在 NVMeVirt 裡，host request 是以 LBA 和 byte count 表示；在 SSD timing backend 裡，需要把它轉成 NAND page operations：

```text
host LBA range
  -> logical pages
  -> FTL mapping
  -> physical page address
  -> channel / chip / LUN / plane / block / page
```

在 MQSim 裡，這些參數會影響：

- Flash page size
- block size
- plane count
- die/LUN parallelism
- NAND read/program/erase latency
- GC cost
- over-provisioning
- mapping table size

在我們自己的 lightweight timing backend 中，這些參數則會變成 resource model：

```text
channel.next_available_time
lun.next_available_time
plane.next_available_time
pcie.next_available_time
controller.next_available_time
```

### 對 DiskANN / ANNS 模擬的意義

DiskANN query search 主要會造成大量 random read。以 NAND 結構來看，一個 candidate node read 可能會經過：

```text
host issues NVMe read
  -> SSD controller parses command
  -> FTL maps node LBA to physical page
  -> selected channel becomes busy
  -> selected LUN performs page read, paying tRD
  -> page data moves through cache/register
  -> data moves over channel/controller
  -> data returns to host over PCIe
  -> host updates candidate list
```

如果一輪 DiskANN search 發出多個 candidate reads，真正決定 round latency 的不是平均 read latency，而是：

```text
max(completion_time of all required candidate reads)
```

而每個 candidate read 的 completion time 取決於它落在哪個：

```text
channel
chip
LUN
plane
block
page
```

因此，一個好的 DiskANN SSD timing model 必須能回答：

- candidate nodes 是否均勻分散到不同 channels？
- 多個 candidate reads 是否撞到同一個 LUN？
- node record 是不是剛好等於一個 NAND page？
- neighbor list 和 vector data 是否放在同一頁？
- 是否能利用 cache read 或 read-ahead？
- host 與 SSD 之間傳了多少 bytes？
- 如果 distance compute 下推到 SSD，省下多少 PCIe D2H transfer？

這些問題比單純設定一個固定 `read_latency = 25us` 更重要，因為 ANNS search 的瓶頸常常來自大量 dependent random I/O 和 host-SSD round trip。

### 第一版建模建議

第一版可以先採用以下簡化：

```text
NAND page size:
  4KiB main data

NAND block:
  64 pages per block

LUN:
  single LUN per chip

Plane:
  two planes per LUN, first version only used for address mapping

Read:
  tRD + channel transfer + PCIe D2H

Write:
  PCIe H2D + write buffer + tPROG

Erase:
  tERASE

ECC:
  fixed decode latency

Bad block:
  reserve a fixed fraction or use minimum good block count
```

之後如果要提高準確度，再逐步加入：

- multi-plane operation
- cache read pipeline
- die-level interleaving
- GC foreground interference
- erase count dependent latency
- read retry / ECC latency variation
- VUC-specific SSD compute units
