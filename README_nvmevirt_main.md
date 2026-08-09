# NVMeVirt `main.c` 架構說明

這份文件用中文整理 `nvmevirt/main.c` 的主要責任。程式碼中的註解維持英文，這份 README 則用來幫助閱讀整體流程。

## 1. `main.c` 在 NVMeVirt 中的角色

`main.c` 是 NVMeVirt kernel module 的入口與資源管理中心。它本身不是每筆 I/O 搬資料的地方，也不是完整 FTL 實作所在的位置。

它主要負責：

- 定義 `insmod nvmev.ko` 時可傳入的 module parameters。
- 驗證 reserved memory 是否正確。
- 把 reserved physical memory 映射成 kernel virtual address。
- 建立 NVMe namespace。
- 初始化 virtual PCI/NVMe device。
- 啟動 dispatcher thread 與 I/O worker threads。
- 建立 `/proc/nvmev/` 控制與觀察介面。
- 初始化我們新增的 MQSim IPC endpoint。
- 在 `rmmod` 時照順序清理資源。

更簡單地說，`main.c` 是 NVMeVirt 的「總開關」。

## 2. Reserved Memory 與 Backing Store

NVMeVirt 不把 virtual SSD 的資料存在一般檔案裡，而是要求 Linux 開機時先用 `memmap=` 保留一段 physical DRAM。

概念上這段 memory 會被切成：

```text
memmap_start
  + 0 ~ 1 MiB
      virtual PCI/NVMe metadata
      BAR
      doorbell registers
      MSI-X table

  + 1 MiB ~ memmap_size
      virtual SSD storage area
      也就是 backing store
```

`main.c` 裡的關鍵設定是：

```c
config->storage_start = memmap_start + MB(1);
config->storage_size = memmap_size - MB(1);
```

接著在 `NVMEV_STORAGE_INIT()` 中：

```c
nvmev_vdev->storage_mapped = memremap(
    nvmev_vdev->config.storage_start,
    nvmev_vdev->config.storage_size,
    MEMREMAP_WB
);
```

這代表：

- `memmap_start` / `memmap_size` 是 physical memory 範圍。
- `storage_mapped` 是 kernel C code 可以使用的 virtual address。
- 後續 namespace 的 `ns[i].mapped` 會指向這段 backing store 的某個 offset。
- host 寫入 `/dev/nvmeXnY` 的資料最後會被 copy 到這裡。
- host 讀取 `/dev/nvmeXnY` 時，資料會從這裡 copy 回 host buffer。

對我們的 DiskANN 實驗來說，preload index 到 NVMeVirt 的意思就是：把 index files 寫進 NVMeVirt block device，最後資料會落在這段 backing store。

## 3. Module Parameters

`main.c` 定義了很多 `module_param()`。

最重要的是：

```text
memmap_start
memmap_size
cpus
read_time
read_delay
read_trailing
write_time
write_delay
write_trailing
nr_io_units
io_unit_shift
```

典型載入方式：

```bash
sudo insmod nvmev.ko memmap_start=128G memmap_size=64G cpus=7,8
```

其中：

- `memmap_start` / `memmap_size` 必須和 GRUB 裡的 `memmap=` reserved region 對得上。
- `cpus` 的第一個 CPU 會給 dispatcher thread。
- `cpus` 後面的 CPU 會給 I/O worker threads。
- read/write timing 參數是 NVMeVirt 內建 local timing model 的 baseline。

接 MQSim 之後，如果 `mqsim_ipc_enable=1` 且 userspace daemon 正常回覆，實際 I/O completion deadline 會優先使用 MQSim 回傳的 latency。

## 4. Dispatcher Thread

`nvmev_dispatcher()` 是 NVMeVirt 的前端 event pump。

它主要輪詢兩種 host-visible state：

```text
BAR access
doorbell updates
```

NVMe host driver 送 command 時，會更新 submission queue tail doorbell。NVMeVirt 在 `nvmev_proc_dbs()` 裡偵測 doorbell 變化。

如果是 admin queue：

```text
qid = 0
-> nvmev_proc_admin_sq()
-> nvmev_proc_admin_cq()
```

如果是 I/O queue：

```text
qid >= 1
-> nvmev_proc_io_sq()
-> io.c 解析 NVMe READ/WRITE command
-> namespace proc_io_cmd() 計算 timing
-> request 進入 I/O worker queue
```

dispatcher 不直接 copy data，也不直接填 completion queue entry。真正的資料搬移與 completion deadline 控制主要在 `io.c` 的 I/O worker path。

## 5. Namespace 初始化

`NVMEV_NAMESPACE_INIT()` 會根據 Kbuild 選到的 SSD type 建立 namespace。

NVMeVirt 支援：

```text
SSD_TYPE_NVM
SSD_TYPE_CONV
SSD_TYPE_ZNS
SSD_TYPE_KV
```

對應初始化函式：

```text
simple_init_namespace()
conv_init_namespace()
zns_init_namespace()
kv_init_namespace()
```

每個 namespace 會設定：

```text
ns[i].id
ns[i].size
ns[i].mapped
ns[i].proc_io_cmd
```

其中 `ns[i].proc_io_cmd` 很重要。`io.c` 收到 NVMe I/O command 後，會透過這個 callback 進入不同 SSD model 的 timing / FTL path。

我們接 MQSim 時，不是直接取代 namespace，而是在 `io.c` 取得 local timing 後，再用 MQSim IPC 回傳的 latency 覆蓋 `ret.nsecs_target`。

## 6. `/proc/nvmev/` 控制介面

`NVMEV_STORAGE_INIT()` 也會建立 procfs 節點：

```text
/proc/nvmev/read_times
/proc/nvmev/write_times
/proc/nvmev/io_units
/proc/nvmev/stat
/proc/nvmev/debug
```

用途：

- `read_times`：讀取或修改 local read timing。
- `write_times`：讀取或修改 local write timing。
- `io_units`：讀取或修改 local I/O parallelism knob。
- `stat`：觀察每個 queue 的 dispatch、in-flight、total I/O。
- `debug`：預留 debug。

這些參數仍然有用，因為它們可以當作：

- MQSim IPC 尚未開啟時的 baseline。
- MQSim daemon timeout/fallback 時的 local model。
- 與 MQSim timing 做 sanity check 的比較組。

## 7. MQSim IPC 初始化位置

我們新增的 MQSim IPC 在 `NVMeV_init()` 裡初始化：

```c
if (nvmev_mqsim_ipc_init()) {
    goto ret_err;
}
```

它的位置在：

```text
storage init
namespace init
MQSim IPC init
PCI init
I/O worker init
dispatcher init
```

這樣設計的意思是：

- backing store 和 namespace 先準備好。
- MQSim IPC endpoint 接著建立。
- 等 virtual PCI/NVMe device 真的對 host 可見時，I/O path 已經可以問 userspace daemon timing。

目前 IPC 預設不改變行為，只有在 `mqsim_ipc_enable=1` 時才會啟用。

## 8. Module Init / Exit 流程

載入 module 時，`NVMeV_init()` 大致做：

```text
print base config
VDEV_INIT
load configs
storage init
namespace init
MQSim IPC init
optional DMA init
PCI init
I/O worker init
dispatcher init
pci_bus_add_devices
```

卸載 module 時，`NVMeV_exit()` 大致做：

```text
pci_stop_root_bus
pci_remove_root_bus
stop dispatcher
stop I/O workers
namespace final
MQSim IPC exit
storage final
DMA cleanup
free SQ/CQ
VDEV_FINALIZE
```

這個順序很重要，因為不能在 worker thread 還可能使用 queue 或 backing store 時，就先把 namespace/storage 釋放掉。

## 9. 對整合 MQSim 的意義

從整合角度看，`main.c` 主要提供三個基礎：

1. **真實資料存放處**

   `storage_mapped` 是 NVMeVirt backing store，DiskANN index preload 後真正 bytes 會在這裡。

2. **host-visible NVMe device**

   `NVMEV_PCI_INIT()` 和 `pci_bus_add_devices()` 讓 Linux host NVMe driver 看到一顆真正的 `/dev/nvmeXnY`。

3. **timing path 的啟動點**

   dispatcher 和 I/O worker thread 啟動後，host I/O 才會進入 `io.c`，而 MQSim latency override 也發生在那條 path 上。

所以 `main.c` 本身不是 MQSim timing model 的核心，但它決定了整個 virtual SSD 是否能被 host 看見、是否有 backing store、以及 I/O path 是否能開始運作。
