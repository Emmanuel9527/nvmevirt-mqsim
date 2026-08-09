# NVMeVirt + MQSim 整合架構 v1

本文件描述第一版 NVMeVirt + MQSim 整合架構的設計方向。第一版目標不是建立完全等同真實商用 SSD 的模擬器，而是建立一個可執行、可量測、可逐步擴充的研究平台，用來評估 DiskANN/ANNS 類 workload 在不同 SSD-side 架構下的 timing behavior。

本版先聚焦兩個核心問題：

1. 如何把 DiskANN index/data 放進 NVMeVirt 的 backing store。
2. 如何實作 NVMeVirt 與 MQSim 之間的 IPC，讓 MQSim 提供動態 latency。

## 1. Dataset / Index 如何放入 NVMeVirt Backing Store

### 1.1 設計目標

DiskANN search 必須讀到真正的 index bytes，才能正確進行 candidate expansion、distance computation、visited set update 與 candidate list maintenance。因此，MQSim 不適合作為真實資料來源，因為 MQSim 原本只模擬 timing、FTL、GC、NAND hierarchy 與 metadata 狀態，並不保存完整 page payload。

第一版設計中，真實資料只放在 NVMeVirt：

```text
DiskANN process
  -> Linux filesystem / block layer
  -> NVMe driver
  -> NVMeVirt
      -> backing store stores real index bytes
  -> MQSim only provides timing
```

換句話說：

```text
NVMeVirt:
  保存真正資料 bytes
  對 host 暴露 /dev/nvmeXnY
  負責把資料 copy/DMA 到 host buffer

MQSim:
  不保存真正資料
  保存 SSD internal timing state
  模擬 FTL、GC、queueing、NAND read/program/erase
```

### 1.2 NVMeVirt Backing Store 是什麼

NVMeVirt 的 backing store 不是一般檔案，也不是 `kmalloc()` 出來的一大塊 kernel heap。NVMeVirt 需要在開機時透過 Linux kernel command line 的 `memmap=` 保留一段實體 DRAM，之後 kernel module 用 `memremap()` 把這段 reserved physical memory 映射進 kernel virtual address space。

概念如下：

```text
reserved physical memory
  + 0 ~ 1 MiB:
      NVMeVirt metadata / BAR / doorbell / MSI-X table

  + 1 MiB ~ memmap_size:
      virtual SSD storage area
```

如果載入 module 時使用：

```bash
sudo insmod nvmev.ko memmap_start=128G memmap_size=64G cpus=7,8
```

則 NVMeVirt 會把這段 reserved physical memory 當作虛擬 SSD 的內容空間。Host 寫入 `/dev/nvmeXn1` 時，資料最後會被 NVMeVirt copy 到這段 backing store；host 讀取 `/dev/nvmeXn1` 時，資料會從 backing store copy 回 host buffer。

因此，所謂 preload index 到 NVMeVirt，語意上是：

```text
把 DiskANN index files 寫入 NVMeVirt 提供的 block device
```

而不是：

```text
把整個 index load 到 DiskANN process 的 host DRAM cache
```

### 1.3 第一版資料放置流程

以目前的 SIFT1M DiskANN index 為例，已建好的 index 位於：

```text
/home/emmanuel/projects/data/sift1m_diskann_indexes
```

其中 default index prefix 為：

```text
sift1m_l2_R64_L100_pq0_default
```

query 階段主要會使用：

```text
sift1m_l2_R64_L100_pq0_default_disk.index
sift1m_l2_R64_L100_pq0_default_pq_compressed.bin
sift1m_l2_R64_L100_pq0_default_pq_pivots.bin
```

第一版建議採用 preload static index 的方式：

```text
1. 載入 NVMeVirt kernel module
2. 在 /dev/nvmeXn1 上建立 filesystem，例如 ext4
3. mount NVMeVirt device 到某個 mount point
4. 將 DiskANN final index files copy 到該 mount point
5. sync，確保資料真的寫入 NVMeVirt backing store
6. drop host page cache
7. query 階段 DiskANN 只讀 NVMeVirt 上的 index files
```

流程示意：

```text
offline index files
  -> cp/write
  -> /mnt/nvmevirt/sift1m_index/
  -> Linux filesystem
  -> NVMeVirt block device
  -> NVMeVirt reserved-memory backing store
```

在 query 階段：

```text
DiskANN read(index offset)
  -> NVMeVirt receives NVMe READ
  -> NVMeVirt asks MQSim for simulated completion time
  -> NVMeVirt waits until simulated completion time
  -> NVMeVirt copies real bytes from backing store to host buffer
  -> DiskANN receives data and continues computation
```

### 1.4 為什麼第一版選 Preload 而不是 Build-Time Writes

DiskANN index build 會產生大量中間檔、temporary shards、memory index、PQ files 與 final disk index。若第一版讓所有 build-time writes 都經過 NVMeVirt + MQSim，會讓系統先卡在 index build 的 write path、filesystem metadata、GC、FTL state synchronization，而不是 query timing。

第一版研究重點是 query search timing，因此比較適合先使用：

```text
offline build index
preload final index
query only through NVMeVirt
```

這樣可以把問題縮小成：

```text
DiskANN query reads
NVMeVirt data correctness
MQSim read timing
host/SSD data exchange
```

build-time writes 可以留到後續版本研究：

```text
online insert/delete
dynamic index maintenance
write-heavy ANNS updates
GC-sensitive workload
```

### 1.5 計時可能不準確的因素

雖然資料存在 NVMeVirt backing store，timing 由 MQSim 控制，但仍有幾個因素可能讓量測結果不準。

#### Host Page Cache

如果 DiskANN 透過一般 filesystem read，Linux 可能把 index file cache 在 host DRAM。第一次 query 讀 NVMeVirt，後續 query 可能直接從 page cache 命中，完全不再送 NVMe request。

這會造成：

```text
實驗以為在測 SSD read latency
實際上測到 host DRAM cache latency
```

需要處理方式：

```text
使用 direct I/O / O_DIRECT / DiskANN aligned read path
或在實驗前 drop caches
記錄每次 query 是否真的產生 NVMe request
```

#### Filesystem Layout 與 Metadata I/O

DiskANN index files 放在 ext4/xfs 等 filesystem 上時，host read 的 LBA 不只受 file offset 影響，也受 filesystem block allocation、extent layout、metadata read 影響。

可能造成：

```text
同一份 index copy 到不同 filesystem 位置
physical LBA layout 不同
MQSim channel/chip/LUN mapping 也不同
```

第一版需要固定流程：

```text
format device
copy index
sync
不要在同一 filesystem 混入其他檔案
記錄 filefrag / extent layout
```

#### NVMeVirt Backing Store 是 DRAM

NVMeVirt backing store 物理上是 DRAM，所以真正 memcpy 很快。這是設計上可接受的，因為 NAND latency、FTL latency、GC latency 由 MQSim 補上。

但必須避免把 memcpy 時間誤解成 SSD latency：

```text
NVMeVirt memcpy/DMA time:
  data correctness cost

MQSim simulated latency:
  SSD timing cost
```

最後 host-visible completion time 應由 MQSim simulated completion time 主導，而不是由 backing store memcpy 完成時間主導。

#### Preload 寫入造成的 MQSim State 不一致

如果 index files 寫入 NVMeVirt backing store，但 MQSim 沒有收到相同的 write events，MQSim 的 FTL state 會是空的。此時 query read 雖然能從 NVMeVirt 讀到真資料，但 MQSim 可能不知道這些 LBA 已經被寫過，也無法模擬正確的 mapping/GC state。

第一版至少需要做其中一種：

```text
方案 A:
  preload 時每個 write 也送到 MQSim

方案 B:
  preload 後根據 occupied LBA range 建立 MQSim preconditioning state

方案 C:
  query-only 第一版先用簡化 mapping，假設所有 read LBA 都有效
```

若要研究 read-only DiskANN query，方案 C 可以作為最小 prototype；若要研究 FTL/GC 對 timing 的影響，必須使用方案 A 或 B。

#### MQSim Latency 與 Real Wall-Clock 對齊

MQSim 是 discrete-event simulator，NVMeVirt 是 real-time kernel module。整合時要把 simulated latency 轉換成 real wall-clock deadline：

```text
submit_wall_time = NVMeVirt 收到 request 的時間
sim_latency = MQSim 回傳的 latency
completion_deadline = submit_wall_time + sim_latency
```

若 MQSim 回覆太慢：

```text
mqsim_reply_time > completion_deadline
```

NVMeVirt 不可能回到過去，只能晚完成 request。這種情況需要記錄為 deadline miss，否則 latency 結果會被 IPC 或 MQSim runtime 污染。

## 2. NVMeVirt 與 MQSim IPC 設計

### 2.1 設計目標

IPC 的目標是讓 NVMeVirt 在收到真實 NVMe request 後，可以把 request 轉成 MQSim 可以理解的 timing event，並取得 simulated completion time。

基本流程：

```text
Host submits NVMe command
  -> NVMeVirt parses command
  -> NVMeVirt sends timing request to MQSim
  -> MQSim updates SSD internal state
  -> MQSim returns simulated completion time
  -> NVMeVirt delays NVMe completion
```

MQSim 不需要回傳真資料，只需要回傳：

```text
request_id
simulated_completion_time
optional latency breakdown
```

### 2.2 Timing Request 格式

第一版可以先定義一個簡化 request 格式：

```text
struct timing_request {
    u64 request_id;
    u64 submit_time_ns;
    u16 opcode;
    u16 queue_id;
    u32 namespace_id;
    u64 start_lba;
    u32 lba_count;
    u32 byte_count;
    u32 flags;
};
```

對 DiskANN read-heavy workload，最重要的是：

```text
opcode
start_lba
byte_count
queue_id
submit_time_ns
```

若後續加入 VUC，可以擴充：

```text
vuc_opcode
query_id
candidate_count
host_to_ssd_bytes
ssd_to_host_bytes
ssd_compute_type
```

### 2.3 Timing Response 格式

MQSim 回傳：

```text
struct timing_response {
    u64 request_id;
    u64 simulated_completion_time_ns;
    u64 simulated_latency_ns;
    u64 ftl_time_ns;
    u64 queueing_time_ns;
    u64 nand_time_ns;
    u64 pcie_time_ns;
    u64 gc_time_ns;
    u32 status;
};
```

第一版最少需要：

```text
request_id
simulated_completion_time_ns
status
```

latency breakdown 可以先作為 debug/statistics。

### 2.4 IPC 實作選項

第一版建議優先考慮 shared memory ring buffer + event notification。

概念：

```text
NVMeVirt kernel module
  -> timing_request ring
  -> notify MQSim daemon

MQSim daemon
  -> poll/read timing_request
  -> simulate request
  -> write timing_response ring
  -> notify NVMeVirt
```

可選通知機制：

```text
eventfd
ioctl
netlink
char device + mmap
poll/epoll
```

第一版如果要快速做出來，可以先用 character device + ioctl 或 netlink；如果之後 IPC overhead 太高，再換 shared memory ring。

### 2.5 Request Pending 機制

NVMeVirt 收到 request 後不能立刻做 completion，而是要建立 pending entry：

```text
pending_table[request_id] = {
    sqid,
    sq_entry,
    opcode,
    lba,
    size,
    host_prp,
    submit_wall_time,
    mqsim_state
}
```

狀態機可以設計成：

```text
RECEIVED
  -> SENT_TO_MQSIM
  -> MQSIM_RESPONDED
  -> WAITING_FOR_DEADLINE
  -> DATA_COPIED
  -> COMPLETED
```

當 MQSim response 回來：

```text
if now < simulated_completion_time:
    arm timer / enqueue delayed completion
else:
    mark deadline miss
    complete as soon as possible
```

到 deadline 時：

```text
read:
  copy backing store -> host PRP buffer

write:
  copy host PRP buffer -> backing store

then:
  post NVMe completion
```

### 2.6 MQSim Runtime 模式

MQSim 原本是 standalone discrete-event simulator。整合後需要提供 daemon/API 模式：

```text
mqsim_daemon:
  init SSD config
  init FTL/GC/preconditioning state
  receive timing_request
  convert NVMe request -> MQSim transaction
  advance simulation state
  return completion timestamp
```

第一版可以先限制：

```text
只支援 READ
固定 namespace
不支援 flush/fua/discard
不支援真 payload
不支援 dynamic write-heavy state
```

等 read-only DiskANN query 跑通後，再逐步加入：

```text
WRITE
preload write replay
GC-sensitive workload
VUC
LUN-level accelerator timing
```

### 2.7 IPC 可能發生的問題

#### IPC Latency 污染

如果每個 request 都要 kernel -> userspace -> kernel round trip，IPC 可能比某些 small read 的 simulated latency 還慢。

需要記錄：

```text
ipc_send_time
ipc_receive_time
mqsim_compute_time
response_delivery_time
deadline_miss
```

若 deadline miss 很多，代表 MQSim daemon 太慢，必須：

```text
減少 IPC 次數
batch requests
使用 shared memory ring
把 hot path timing model 搬進 kernel
或讓 MQSim 只做 offline calibration
```

#### Request Ordering 不一致

NVMe 支援多 queue，DiskANN 也可能發多個 async reads。NVMeVirt 和 MQSim 必須看到相同的 request order、queue id 與 submit time，否則 MQSim 的 internal queueing 會不準。

需要在 request 中保存：

```text
queue_id
submission_order
submit_time_ns
request_id
```

MQSim 端不可只用收到 IPC 的順序當作唯一順序，因為 IPC delivery order 可能和 NVMeVirt parse order 不完全一致。

#### MQSim Sim-Time 與 Wall-Time Drift

MQSim 的 simulated time 可能前進得比 real wall-clock 快或慢。NVMeVirt 需要的是可落地的 wall-clock deadline。

第一版可採用：

```text
simulated_latency_ns = MQSim completion_sim_time - request_submit_sim_time
completion_wall_deadline = submit_wall_time + simulated_latency_ns
```

也就是 MQSim 回傳 latency delta，而不是要求 NVMeVirt 完全使用 MQSim 的 absolute simulated time。

#### Backpressure

如果 DiskANN queue depth 很高，NVMeVirt 可能短時間送出大量 timing requests。MQSim daemon 如果處理不完，request ring 會滿。

需要定義：

```text
ring full 時 NVMeVirt 要等待？
還是 fallback 到簡化 latency？
還是回錯？
```

研究用途建議：

```text
ring full -> 記錄錯誤並阻塞/等待
不要 silently fallback
```

否則結果會混入不同 timing model。

#### Crash / Recovery

MQSim daemon 如果 crash，NVMeVirt pending requests 會永遠等不到 response。

第一版至少要有 timeout：

```text
MQSim response timeout
  -> fail request
  -> 或使用 emergency fallback latency
  -> 記錄 fatal error
```

實驗模式下建議直接 fail-fast，避免產生看似正常但其實錯誤的結果。

#### Write Path Consistency

如果支援 write，NVMeVirt backing store 與 MQSim FTL state 必須同步：

```text
NVMeVirt 寫入真資料
MQSim 更新 FTL mapping
```

需要決定 write completion policy：

```text
early completion:
  host data copied into NVMeVirt buffer 後即可 complete
  MQSim NAND program 在背景完成

strict completion:
  等 MQSim NAND program completion 才 complete
```

第一版 read-only DiskANN query 可以先避開這個問題；但 preload 或 future update workload 一定會遇到。

### 2.8 第一版建議

第一版最小可行設計：

```text
資料：
  SIFT1M final DiskANN index preload 到 NVMeVirt backing store

I/O：
  DiskANN query 只讀 NVMeVirt

MQSim：
  daemon mode
  只保存 timing/FTL/NAND state
  read-only timing path 先跑通

IPC：
  先用簡單 char device/ioctl 或 netlink
  request/response 加 request_id
  記錄 IPC latency 與 deadline miss

completion：
  NVMeVirt pending request
  MQSim 回 latency
  NVMeVirt 到 deadline 才 copy data + complete
```

這個版本的研究價值是先確認：

```text
DiskANN 是否真的能透過 NVMeVirt 讀到正確 index data
MQSim 是否能對每個 read 產生動態 latency
host-visible latency 是否能被 NVMeVirt deadline 控制
IPC overhead 是否會破壞 timing accuracy
```

等這些跑通後，再進一步加入：

```text
preload write replay
more accurate FTL state
GC interference
VUC command path
LUN-level accelerator timing
```
