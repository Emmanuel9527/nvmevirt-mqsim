# NVMeVirt + MQSim Timing Model 設計

這份文件說明目前打算如何在 NVMeVirt + MQSim 整合專案中設計 timing model。目標不是做到 cycle-level、百分之百等同真實商用 SSD，而是要讓 timing 足夠合理，能用來比較不同 host/SSD 架構對 ANNS/DiskANN 類 workload 的速度影響。

核心想法是：

```text
NVMeVirt 負責真實 host-facing NVMe I/O path
MQSim 負責提供 SSD 內部架構與 timing 的參考模型
NVMeVirt runtime 內放一個 lightweight event-driven timing backend
```

也就是說，DiskANN 或其他 host application 仍然真的對 NVMeVirt 暴露出的 NVMe device 發 I/O。NVMeVirt 收到 command 後，解析 opcode、LBA、size、queue id 與 VUC metadata，再交給 timing backend 計算 simulated completion timestamp。NVMeVirt 最後依照這個 timestamp 延遲完成 NVMe command。

MQSim 不建議在每個小 I/O 或每個內部 event 上都透過 kernel/userspace round trip 即時呼叫。這樣會把 IPC、context switch、userspace scheduling 的成本混進 SSD latency，對 DiskANN 或 VUC 這種 latency-sensitive workload 會造成污染。比較合理的做法是：MQSim 作為參數來源與 validation reference，runtime 則在 NVMeVirt 內使用較輕量、可解釋、event-driven 的 timing backend。

## 責任分工

NVMeVirt 負責真實 host 看得到的路徑：

- NVMe command parsing
- submission queue / completion queue behavior
- Linux block layer 與 NVMe driver interaction
- host memory 與 virtual device 之間的 DMA/data movement
- 根據 simulated completion time 延遲 request completion
- 透過真實 NVMe command path 暴露 VUC

MQSim 或 MQSim-derived timing backend 負責 SSD 內部 timing：

- FTL lookup latency
- NAND read/program/erase latency
- NAND channel、chip、die/LUN、plane contention
- PCIe host-to-device 與 device-to-host transfer time
- SSD DRAM/SRAM/cache access latency
- SSD-side compute latency，例如 VUC 或 near-data processing
- foreground I/O 受到 GC/background work 影響時的 queueing delay

第一版實作不需要把完整 MQSim runtime port 進 kernel。可以先用 resource reservation model，也就是每個共享資源都有自己的 `next_available_time`：

```text
pcie_h2d.next_available_time
pcie_d2h.next_available_time
controller.next_available_time
dram.next_available_time
channel[i].next_available_time
chip[i].next_available_time
lun[i].next_available_time
plane[i].next_available_time
ssd_compute_unit[i].next_available_time
```

當一個 event 要使用某個 resource 時，timing backend 計算：

```text
start_time  = max(event_ready_time, resource.next_available_time)
finish_time = start_time + fixed_latency + transfer_size / bandwidth
resource.next_available_time = finish_time
```

這種模型本質上仍然是 event-driven：每個 NVMe request 會被拆成有 dependency 的 timing events，每個 event 會保留它用到的資源，最後得到 request 的 completion time。

## Datasheet LUN 與 SSD-Level LUN

NAND datasheet 描述的是單顆 NAND device，不等於完整 SSD。以目前參考的 `MX35LF4G24AD` 為例，datasheet 的 parameter page 顯示 `Number of Logical Units = 1`。這代表單顆 `MX35LF4G24AD` device 內部可以先建成：

```text
1 NAND chip/device
  -> 1 LUN
      -> 2 planes
          -> blocks
              -> pages
```

但這不代表整顆 SSD 只能有 1 個 LUN。完整 SSD 會把多顆 NAND chips/packages 接到多個 channels 上；如果 package 內還有多個 die，也可能形成更多 LUN。因此 MQSim 層級應該要模擬多個 channel、chip、die/LUN，讓整顆 SSD 具有合理的 internal parallelism。

一個較合理的 SSD-level model 會像這樣：

```text
SSD
  -> channel 0
      -> chip 0
          -> LUN 0
              -> plane 0
              -> plane 1
      -> chip 1
          -> LUN 0
              -> plane 0
              -> plane 1
  -> channel 1
      -> chip 0
          -> LUN 0
              -> plane 0
              -> plane 1
      -> chip 1
          -> LUN 0
              -> plane 0
              -> plane 1
```

如果使用 multi-die package，也可以建成：

```text
channel
  -> package/chip
      -> die/LUN 0
      -> die/LUN 1
      -> die/LUN 2
      -> die/LUN 3
```

因此設計上應該分成兩層：

```text
NAND datasheet:
  提供單顆 NAND device 的 page/block/plane/timing 參數

MQSim SSD config:
  決定整顆 SSD 有幾個 channel、chip/package、die/LUN、plane
```

例如第一版可以設定：

```text
channels = 8
chips_per_channel = 4
luns_per_chip = 1
planes_per_lun = 2
```

這樣整顆 SSD 共有：

```text
total_luns = 8 * 4 * 1 = 32
```

也就是 32 個 NAND array-operation scheduling resources。DiskANN 一輪如果發出多個 random reads，這些 reads 就有機會分散到不同 channel 或 LUN 平行執行。這一點很重要，因為 DiskANN 一輪 search 的 latency 通常取決於該輪最慢完成的 candidate read；如果沒有多 LUN/channel parallelism，tail latency 會被嚴重高估，也無法比較不同 SSD 架構的 parallelism。

如果之後要更接近現代 SSD，可以設定：

```text
channels = 8
chips_per_channel = 4
dies_per_chip = 2 或 4
planes_per_die = 2
```

這時候：

```text
total_luns = channels * chips_per_channel * dies_per_chip
```

總結來說，datasheet 的 `1 LUN` 只應該用來描述單顆 NAND chip/device；MQSim 的 SSD-level model 應該模擬多顆 NAND device 組成的多 LUN SSD。

## DiskANN Query Search Timing 範例

DiskANN search 很適合用來說明 timing model，因為一個 query 不是單一 SSD read。它會進行多輪 dependent random reads，並在 host 端維護 candidate list。每一輪大致會：

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

假設 host-centric DiskANN 一輪選出 `W = 8` 個 candidate nodes，host 會發出 8 個 asynchronous random reads：

```text
read(node_0_record)
read(node_1_record)
...
read(node_7_record)
```

NVMeVirt 會觀察到這些真實 read requests，並把每個 read 轉成 SSD timing request：

```text
submit_time
queue_id
opcode = READ
lba
read_size
request_id
```

Timing backend 會把 LBA 映射到 SSD 內部位置，例如：

```text
channel
chip/package
die/LUN
plane
block
page
```

接著用 MQSim-style 的 SSD timing 計算每個 node read 的完成時間：

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

這 8 個 reads 不一定會 serialize。如果它們落在不同 channel 或不同 LUN，就可以平行；如果撞到同一個 channel、chip 或 LUN，就要依照該 resource 的 `next_available_time` 排隊。例如：

```text
node_0 -> channel 0, chip 0, LUN 0
node_1 -> channel 3, chip 2, LUN 0
node_2 -> channel 1, chip 1, LUN 0
node_3 -> channel 0, chip 0, LUN 0
```

`node_0` 和 `node_3` 因為落在同一組 channel/chip/LUN，所以可能互相排隊；其他 node reads 如果落在不同資源上，就可能同時進行。

一輪 DiskANN search 的 I/O 完成時間通常取決於該輪需要等待的最慢 read：

```text
round_io_done_time = max(
    completion_time(node_0),
    completion_time(node_1),
    ...
    completion_time(node_7)
)
```

如果 host 是等整個 beam 都回來後才 compute distance，那這輪完成時間可以寫成：

```text
round_done_time =
  round_io_done_time
+ T_host_distance_compute(returned_nodes)
+ T_candidate_list_update
```

如果 host 可以在每個 I/O completion 後立刻 compute distance，那 host compute 可以和剩下的 SSD read overlap。這時候 event graph 應該記成：

```text
IO_COMPLETE(node_i)
  -> COMPUTE_DISTANCE(node_i)
  -> UPDATE_CANDIDATE_LIST(node_i)
```

下一輪 search 會在 candidate list 更新到足夠狀態，且 DiskANN termination rule 判斷還需要繼續訪問更多 candidates 時開始。

## Host/SSD Data Exchange Timing

這個專案特別需要明確記錄 host 與 SSD 之間的資料交換時間，因為 ANNS/VUC 設計可能會有大量小型互動。Timing model 不能只記一個總 latency，而應該分開記錄 PCIe transfer、NAND access、SSD compute 與 host compute。

每個 command 或 VUC 至少應記錄：

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

一般 host-centric DiskANN read 主要是 SSD-to-host traffic，因為 SSD 會把 node record 傳回 host。若改成 SSD-assisted design，host 可能先把 query vector 或 candidate list 傳到 SSD，SSD 則只回傳 node id、distance 或 partial top-k result。這會減少 PCIe D2H traffic，但會增加 SSD-side compute 和 SSD-side state management。

例如一個讓 SSD 評估一批 candidates 的 VUC，可以建成：

```text
HOST_TO_SSD_QUERY_VECTOR
  -> SSD_READ_CANDIDATE_NODE_RECORDS
  -> SSD_COMPUTE_DISTANCES
  -> SSD_UPDATE_LOCAL_CANDIDATES
  -> SSD_TO_HOST_PARTIAL_RESULTS
  -> NVME_COMPLETION
```

它的 timing 可以拆成：

```text
T_vuc_batch =
  T_pcie_h2d(query_vector_bytes + command_metadata)
+ T_nand_reads(candidate_node_records)
+ T_ssd_compute(num_candidates, vector_dim)
+ T_candidate_state_update
+ T_pcie_d2h(result_bytes)
+ T_completion
```

這樣才能比較不同架構到底是省下：

- host-side candidate maintenance
- host-to-SSD round trips
- PCIe data movement
- NAND random read latency and contention
- SSD-side compute
- SSD internal queueing delay

## 需要記錄的 Metrics

每次 DiskANN query 不只要記總 latency，也要記錄 latency breakdown。建議至少包含：

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

這些 metrics 可以讓結果更有解釋力。即使模型不是 100% 等於真實 SSD，只要 timing 差異是由明確資源推導出來，就能回答不同 ANNS/SSD 架構為什麼比較快或比較慢。
