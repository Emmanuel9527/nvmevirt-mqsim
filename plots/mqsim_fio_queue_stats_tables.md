# MQSim fio queue-depth stats tables

Source: pasted daemon output from MQSim native online fio run.

## Run setup

- `MQSim native preload extents loaded. extents=8 allocated_pages=115644 source=/tmp/sift1m_nvmevirt_extents.csv`
- `MQSim shared-memory IPC daemon connected. model=native config=./ssdconfig.xml native-event-driven sectors/page=16 channels=8 chips/channel=4 dies/chip=1 preload_requests=115644 preload_sectors=1850288`

## Snapshot summary

| online_reads | requests | completed | pending | max_pending | events_run | flash_reads | mapping_reads | cmt_read_hits | cmt_read_misses | top_max_qlen | top_max_wait_us |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50000 | 165644 | 165643 | 1 | 1 | 852210 | 206974 | 156976 | 8668 | 41332 | 1 | 0 |
| 100000 | 215644 | 215643 | 1 | 4 | 1077348 | 282356 | 182357 | 33287 | 66713 | 1 | 99 |
| 150000 | 265644 | 265643 | 1 | 4 | 1227282 | 332356 | 182357 | 83287 | 66713 | 1 | 99 |
| 200000 | 315644 | 315643 | 1 | 4 | 1456446 | 408749 | 208751 | 106893 | 93107 | 1 | 99 |
| 250000 | 365644 | 365643 | 1 | 8 | 1616846 | 462379 | 212380 | 153264 | 96736 | 1 | 99 |
| 300000 | 415644 | 415643 | 1 | 8 | 1766837 | 512379 | 212380 | 203264 | 96736 | 1 | 99 |
| 350000 | 465644 | 465643 | 1 | 16 | 1951064 | 573870 | 223871 | 241773 | 108227 | 2 | 160 |
| 400000 | 515644 | 515643 | 1 | 16 | 2100872 | 623870 | 223871 | 291773 | 108227 | 2 | 160 |
| 450000 | 565644 | 565643 | 1 | 16 | 2250731 | 673870 | 223871 | 341773 | 108227 | 2 | 160 |
| 500000 | 615644 | 615643 | 1 | 32 | 2413453 | 728366 | 228367 | 387277 | 112723 | 3 | 243 |
| 550000 | 665644 | 665643 | 1 | 32 | 2562280 | 778366 | 228367 | 437277 | 112723 | 3 | 243 |
| 600000 | 715644 | 715643 | 1 | 32 | 2712088 | 828366 | 228367 | 487277 | 112723 | 3 | 243 |

## Distribution summary

| online_reads | distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- | --- |
| 50000 | channel distribution | 12.50 | 12.25 | 12.71 | 322618 |  |
| 50000 | lun distribution | 3.12 | 2.65 | 3.31 | 322618 |  |
| 50000 | read channel distribution | 12.50 | 12.12 | 12.82 |  | 206974 |
| 50000 | read lun distribution | 3.12 | 2.38 | 3.42 |  | 206974 |
| 100000 | channel distribution | 12.50 | 12.31 | 12.67 | 398000 |  |
| 100000 | lun distribution | 3.12 | 2.75 | 3.30 | 398000 |  |
| 100000 | read channel distribution | 12.50 | 12.23 | 12.75 |  | 282356 |
| 100000 | read lun distribution | 3.12 | 2.60 | 3.37 |  | 282356 |
| 150000 | channel distribution | 12.50 | 12.30 | 12.67 | 448000 |  |
| 150000 | lun distribution | 3.12 | 2.79 | 3.30 | 448000 |  |
| 150000 | read channel distribution | 12.50 | 12.23 | 12.73 |  | 332356 |
| 150000 | read lun distribution | 3.12 | 2.67 | 3.36 |  | 332356 |
| 200000 | channel distribution | 12.50 | 12.34 | 12.62 | 524393 |  |
| 200000 | lun distribution | 3.12 | 2.85 | 3.26 | 524393 |  |
| 200000 | read channel distribution | 12.50 | 12.29 | 12.65 |  | 408749 |
| 200000 | read lun distribution | 3.12 | 2.77 | 3.30 |  | 408749 |
| 250000 | channel distribution | 12.50 | 12.35 | 12.62 | 578023 |  |
| 250000 | lun distribution | 3.12 | 2.87 | 3.26 | 578023 |  |
| 250000 | read channel distribution | 12.50 | 12.31 | 12.65 |  | 462379 |
| 250000 | read lun distribution | 3.12 | 2.81 | 3.29 |  | 462379 |
| 300000 | channel distribution | 12.50 | 12.35 | 12.61 | 628023 |  |
| 300000 | lun distribution | 3.12 | 2.90 | 3.25 | 628023 |  |
| 300000 | read channel distribution | 12.50 | 12.32 | 12.63 |  | 512379 |
| 300000 | read lun distribution | 3.12 | 2.85 | 3.28 |  | 512379 |
| 350000 | channel distribution | 12.50 | 12.37 | 12.60 | 689514 |  |
| 350000 | lun distribution | 3.12 | 2.92 | 3.25 | 689514 |  |
| 350000 | read channel distribution | 12.50 | 12.34 | 12.62 |  | 573870 |
| 350000 | read lun distribution | 3.12 | 2.87 | 3.27 |  | 573870 |
| 400000 | channel distribution | 12.50 | 12.37 | 12.61 | 739514 |  |
| 400000 | lun distribution | 3.12 | 2.92 | 3.25 | 739514 |  |
| 400000 | read channel distribution | 12.50 | 12.34 | 12.63 |  | 623870 |
| 400000 | read lun distribution | 3.12 | 2.89 | 3.27 |  | 623870 |
| 450000 | channel distribution | 12.50 | 12.38 | 12.59 | 789514 |  |
| 450000 | lun distribution | 3.12 | 2.94 | 3.24 | 789514 |  |
| 450000 | read channel distribution | 12.50 | 12.36 | 12.61 |  | 673870 |
| 450000 | read lun distribution | 3.12 | 2.91 | 3.26 |  | 673870 |
| 500000 | channel distribution | 12.50 | 12.39 | 12.59 | 844010 |  |
| 500000 | lun distribution | 3.12 | 2.95 | 3.24 | 844010 |  |
| 500000 | read channel distribution | 12.50 | 12.37 | 12.60 |  | 728366 |
| 500000 | read lun distribution | 3.12 | 2.92 | 3.26 |  | 728366 |
| 550000 | channel distribution | 12.50 | 12.38 | 12.59 | 894010 |  |
| 550000 | lun distribution | 3.12 | 2.96 | 3.24 | 894010 |  |
| 550000 | read channel distribution | 12.50 | 12.36 | 12.60 |  | 778366 |
| 550000 | read lun distribution | 3.12 | 2.93 | 3.25 |  | 778366 |
| 600000 | channel distribution | 12.50 | 12.39 | 12.58 | 944010 |  |
| 600000 | lun distribution | 3.12 | 2.97 | 3.24 | 944010 |  |
| 600000 | read channel distribution | 12.50 | 12.38 | 12.59 |  | 828366 |
| 600000 | read lun distribution | 3.12 | 2.95 | 3.26 |  | 828366 |

## Snapshot 1: online_reads=50000, max_pending=1

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 165644 | 165643 | 1 | 0 | 1 | 852210 | 206974 | 115644 | 156976 | 8668 | 41332 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@5@0@HIGH | 1542 | 1542 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |
| Mapping_Read_TR_Queue@5@3 | 5388 | 5388 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |
| User_Write_TR_Queue@5@3@HIGH | 3613 | 3613 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |
| User_Read_TR_Queue@5@3@HIGH | 1593 | 1593 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |
| Mapping_Read_TR_Queue@5@2 | 5325 | 5325 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |
| User_Write_TR_Queue@5@2@HIGH | 3613 | 3613 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |
| User_Read_TR_Queue@5@2@HIGH | 1585 | 1585 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |
| Mapping_Read_TR_Queue@5@1 | 5311 | 5311 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |
| User_Write_TR_Queue@5@1@HIGH | 3614 | 3614 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |
| User_Read_TR_Queue@5@1@HIGH | 1575 | 1575 | 0 | 0.00 | 1 | 0.00 | 0 | 0 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.25 | 12.71 | 322618 |  |
| lun distribution | 3.12 | 2.65 | 3.31 | 322618 |  |
| read channel distribution | 12.50 | 12.12 | 12.82 |  | 206974 |
| read lun distribution | 3.12 | 2.38 | 3.42 |  | 206974 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.31 | 7069 | 3613 | 0 |
| lun23 | 3.28 | 6981 | 3613 | 0 |
| lun27 | 3.27 | 6951 | 3613 | 0 |
| lun10 | 3.27 | 6951 | 3613 | 0 |
| lun11 | 3.27 | 6945 | 3613 | 0 |
| lun15 | 3.27 | 6938 | 3613 | 0 |
| lun2 | 3.27 | 6934 | 3614 | 0 |
| lun19 | 3.27 | 6935 | 3613 | 0 |
| lun6 | 3.27 | 6932 | 3613 | 0 |
| lun18 | 3.27 | 6931 | 3613 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.65 | 4919 | 3615 | 0 |
| lun1 | 2.84 | 5538 | 3615 | 0 |
| lun9 | 2.85 | 5569 | 3614 | 0 |
| lun12 | 2.85 | 5585 | 3615 | 0 |
| lun16 | 2.86 | 5617 | 3615 | 0 |
| lun20 | 2.87 | 5631 | 3615 | 0 |
| lun24 | 2.87 | 5635 | 3615 | 0 |
| lun5 | 2.87 | 5637 | 3615 | 0 |
| lun13 | 2.88 | 5663 | 3614 | 0 |
| lun8 | 2.91 | 5783 | 3615 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.42 | 7069 |
| lun23 | 3.37 | 6981 |
| lun27 | 3.36 | 6951 |
| lun10 | 3.36 | 6951 |
| lun11 | 3.36 | 6945 |
| lun15 | 3.35 | 6938 |
| lun19 | 3.35 | 6935 |
| lun2 | 3.35 | 6934 |
| lun6 | 3.35 | 6932 |
| lun18 | 3.35 | 6931 |

## Snapshot 2: online_reads=100000, max_pending=4

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 215644 | 215643 | 1 | 0 | 4 | 1077348 | 282356 | 115644 | 182357 | 33287 | 66713 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@2@3@HIGH | 3186 | 3186 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@5@0@HIGH | 3048 | 3048 | 0 | 0.00 | 1 | 0.00 | 0 | 92 |
| User_Read_TR_Queue@4@3@HIGH | 3007 | 3007 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@1@3@HIGH | 3296 | 3296 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@5@1@HIGH | 3086 | 3086 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@2@HIGH | 3168 | 3168 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@1@HIGH | 3114 | 3114 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@1@1@HIGH | 3078 | 3078 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@3@2@HIGH | 3191 | 3191 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@7@0@HIGH | 3102 | 3102 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.31 | 12.67 | 398000 |  |
| lun distribution | 3.12 | 2.75 | 3.30 | 398000 |  |
| read channel distribution | 12.50 | 12.23 | 12.75 |  | 282356 |
| read lun distribution | 3.12 | 2.60 | 3.37 |  | 282356 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.30 | 9515 | 3613 | 0 |
| lun11 | 3.25 | 9336 | 3613 | 0 |
| lun2 | 3.25 | 9313 | 3614 | 0 |
| lun23 | 3.25 | 9312 | 3613 | 0 |
| lun15 | 3.24 | 9301 | 3613 | 0 |
| lun10 | 3.24 | 9297 | 3613 | 0 |
| lun3 | 3.24 | 9271 | 3613 | 0 |
| lun25 | 3.23 | 9246 | 3614 | 0 |
| lun18 | 3.23 | 9234 | 3613 | 0 |
| lun6 | 3.23 | 9232 | 3613 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.75 | 7348 | 3615 | 0 |
| lun1 | 2.88 | 7838 | 3615 | 0 |
| lun16 | 2.90 | 7921 | 3615 | 0 |
| lun20 | 2.91 | 7963 | 3615 | 0 |
| lun9 | 2.91 | 7968 | 3614 | 0 |
| lun12 | 2.92 | 8025 | 3615 | 0 |
| lun5 | 2.93 | 8044 | 3615 | 0 |
| lun24 | 2.93 | 8047 | 3615 | 0 |
| lun13 | 2.95 | 8142 | 3614 | 0 |
| lun8 | 2.98 | 8239 | 3615 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.37 | 9515 |
| lun11 | 3.31 | 9336 |
| lun2 | 3.30 | 9313 |
| lun23 | 3.30 | 9312 |
| lun15 | 3.29 | 9301 |
| lun10 | 3.29 | 9297 |
| lun3 | 3.28 | 9271 |
| lun25 | 3.27 | 9246 |
| lun18 | 3.27 | 9234 |
| lun6 | 3.27 | 9232 |

## Snapshot 3: online_reads=150000, max_pending=4

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 265644 | 265643 | 1 | 0 | 4 | 1227282 | 332356 | 115644 | 182357 | 83287 | 66713 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@2@3@HIGH | 4820 | 4820 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@5@0@HIGH | 4569 | 4569 | 0 | 0.00 | 1 | 0.00 | 0 | 92 |
| User_Read_TR_Queue@4@3@HIGH | 4577 | 4577 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@5@1@HIGH | 4628 | 4628 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@1@3@HIGH | 4949 | 4949 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@1@HIGH | 4698 | 4698 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@2@HIGH | 4729 | 4729 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@1@1@HIGH | 4622 | 4622 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@3@2@HIGH | 4763 | 4763 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@0@HIGH | 4653 | 4653 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.30 | 12.67 | 448000 |  |
| lun distribution | 3.12 | 2.79 | 3.30 | 448000 |  |
| read channel distribution | 12.50 | 12.23 | 12.73 |  | 332356 |
| read lun distribution | 3.12 | 2.67 | 3.36 |  | 332356 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.30 | 11168 | 3613 | 0 |
| lun11 | 3.26 | 10970 | 3613 | 0 |
| lun23 | 3.25 | 10935 | 3613 | 0 |
| lun15 | 3.25 | 10925 | 3613 | 0 |
| lun10 | 3.24 | 10883 | 3613 | 0 |
| lun17 | 3.23 | 10871 | 3614 | 0 |
| lun22 | 3.23 | 10838 | 3613 | 0 |
| lun25 | 3.22 | 10830 | 3614 | 0 |
| lun27 | 3.22 | 10830 | 3613 | 0 |
| lun2 | 3.22 | 10814 | 3614 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.79 | 8880 | 3615 | 0 |
| lun1 | 2.89 | 9340 | 3615 | 0 |
| lun16 | 2.92 | 9461 | 3615 | 0 |
| lun9 | 2.92 | 9473 | 3614 | 0 |
| lun20 | 2.92 | 9484 | 3615 | 0 |
| lun12 | 2.94 | 9571 | 3615 | 0 |
| lun5 | 2.95 | 9588 | 3615 | 0 |
| lun24 | 2.95 | 9589 | 3615 | 0 |
| lun13 | 2.98 | 9729 | 3614 | 0 |
| lun8 | 3.00 | 9822 | 3615 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.36 | 11168 |
| lun11 | 3.30 | 10970 |
| lun23 | 3.29 | 10935 |
| lun15 | 3.29 | 10925 |
| lun10 | 3.27 | 10883 |
| lun17 | 3.27 | 10871 |
| lun22 | 3.26 | 10838 |
| lun27 | 3.26 | 10830 |
| lun25 | 3.26 | 10830 |
| lun2 | 3.25 | 10814 |

## Snapshot 4: online_reads=200000, max_pending=4

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 315644 | 315643 | 1 | 0 | 4 | 1456446 | 408749 | 115644 | 208751 | 106893 | 93107 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@2@3@HIGH | 6483 | 6483 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@5@0@HIGH | 6124 | 6124 | 0 | 0.00 | 1 | 0.00 | 0 | 92 |
| User_Read_TR_Queue@4@3@HIGH | 6066 | 6066 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@5@1@HIGH | 6207 | 6207 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@1@3@HIGH | 6514 | 6514 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@1@HIGH | 6241 | 6241 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@2@HIGH | 6304 | 6304 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@1@1@HIGH | 6168 | 6168 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@3@2@HIGH | 6330 | 6330 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@0@HIGH | 6212 | 6212 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.34 | 12.62 | 524393 |  |
| lun distribution | 3.12 | 2.85 | 3.26 | 524393 |  |
| read channel distribution | 12.50 | 12.29 | 12.65 |  | 408749 |
| read lun distribution | 3.12 | 2.77 | 3.30 |  | 408749 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.26 | 13476 | 3613 | 0 |
| lun11 | 3.25 | 13418 | 3613 | 0 |
| lun23 | 3.23 | 13315 | 3613 | 0 |
| lun17 | 3.23 | 13313 | 3614 | 0 |
| lun10 | 3.21 | 13237 | 3613 | 0 |
| lun2 | 3.21 | 13226 | 3614 | 0 |
| lun6 | 3.21 | 13223 | 3613 | 0 |
| lun15 | 3.21 | 13216 | 3613 | 0 |
| lun3 | 3.21 | 13208 | 3613 | 0 |
| lun25 | 3.21 | 13201 | 3614 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.85 | 11320 | 3615 | 0 |
| lun1 | 2.93 | 11747 | 3615 | 0 |
| lun16 | 2.94 | 11825 | 3615 | 0 |
| lun9 | 2.96 | 11896 | 3614 | 0 |
| lun20 | 2.96 | 11910 | 3615 | 0 |
| lun12 | 2.97 | 11962 | 3615 | 0 |
| lun5 | 2.98 | 12004 | 3615 | 0 |
| lun24 | 2.98 | 12013 | 3615 | 0 |
| lun13 | 3.01 | 12167 | 3614 | 0 |
| lun8 | 3.02 | 12214 | 3615 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.30 | 13476 |
| lun11 | 3.28 | 13418 |
| lun23 | 3.26 | 13315 |
| lun17 | 3.26 | 13313 |
| lun10 | 3.24 | 13237 |
| lun2 | 3.24 | 13226 |
| lun6 | 3.23 | 13223 |
| lun15 | 3.23 | 13216 |
| lun3 | 3.23 | 13208 |
| lun25 | 3.23 | 13201 |

## Snapshot 5: online_reads=250000, max_pending=8

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 365644 | 365643 | 1 | 0 | 8 | 1616846 | 462379 | 115644 | 212380 | 153264 | 96736 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@2@3@HIGH | 8081 | 8081 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@5@0@HIGH | 7652 | 7652 | 0 | 0.00 | 1 | 0.00 | 0 | 92 |
| User_Read_TR_Queue@6@3@HIGH | 7824 | 7824 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@5@3@HIGH | 7871 | 7871 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@5@2@HIGH | 7925 | 7925 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@0@HIGH | 7771 | 7771 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@2@1@HIGH | 7612 | 7612 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@5@1@HIGH | 7772 | 7772 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@1@HIGH | 7800 | 7800 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@1@3@HIGH | 8136 | 8136 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.35 | 12.62 | 578023 |  |
| lun distribution | 3.12 | 2.87 | 3.26 | 578023 |  |
| read channel distribution | 12.50 | 12.31 | 12.65 |  | 462379 |
| read lun distribution | 3.12 | 2.81 | 3.29 |  | 462379 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.26 | 15205 | 3613 | 0 |
| lun11 | 3.24 | 15119 | 3613 | 0 |
| lun17 | 3.23 | 15044 | 3614 | 0 |
| lun23 | 3.22 | 15013 | 3613 | 0 |
| lun10 | 3.21 | 14962 | 3613 | 0 |
| lun15 | 3.21 | 14922 | 3613 | 0 |
| lun6 | 3.20 | 14902 | 3613 | 0 |
| lun14 | 3.20 | 14901 | 3613 | 0 |
| lun2 | 3.20 | 14867 | 3614 | 0 |
| lun25 | 3.20 | 14864 | 3614 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.87 | 12970 | 3615 | 0 |
| lun1 | 2.95 | 13420 | 3615 | 0 |
| lun16 | 2.96 | 13484 | 3615 | 0 |
| lun9 | 2.97 | 13533 | 3614 | 0 |
| lun20 | 2.97 | 13577 | 3615 | 0 |
| lun12 | 2.98 | 13610 | 3615 | 0 |
| lun5 | 3.00 | 13708 | 3615 | 0 |
| lun24 | 3.00 | 13711 | 3615 | 0 |
| lun8 | 3.03 | 13885 | 3615 | 0 |
| lun13 | 3.03 | 13893 | 3614 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.29 | 15205 |
| lun11 | 3.27 | 15119 |
| lun17 | 3.25 | 15044 |
| lun23 | 3.25 | 15013 |
| lun10 | 3.24 | 14962 |
| lun15 | 3.23 | 14922 |
| lun6 | 3.22 | 14902 |
| lun14 | 3.22 | 14901 |
| lun2 | 3.22 | 14867 |
| lun22 | 3.21 | 14865 |

## Snapshot 6: online_reads=300000, max_pending=8

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 415644 | 415643 | 1 | 0 | 8 | 1766837 | 512379 | 115644 | 212380 | 203264 | 96736 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@2@3@HIGH | 9715 | 9715 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@5@0@HIGH | 9180 | 9180 | 0 | 0.00 | 1 | 0.00 | 0 | 92 |
| User_Read_TR_Queue@6@3@HIGH | 9408 | 9408 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@5@3@HIGH | 9436 | 9436 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@5@2@HIGH | 9517 | 9517 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@0@HIGH | 9304 | 9304 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@2@1@HIGH | 9139 | 9139 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@5@1@HIGH | 9324 | 9324 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@1@HIGH | 9353 | 9353 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@1@3@HIGH | 9759 | 9759 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.35 | 12.61 | 628023 |  |
| lun distribution | 3.12 | 2.90 | 3.25 | 628023 |  |
| read channel distribution | 12.50 | 12.32 | 12.63 |  | 512379 |
| read lun distribution | 3.12 | 2.85 | 3.28 |  | 512379 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.25 | 16828 | 3613 | 0 |
| lun11 | 3.24 | 16753 | 3613 | 0 |
| lun17 | 3.23 | 16662 | 3614 | 0 |
| lun23 | 3.22 | 16578 | 3613 | 0 |
| lun15 | 3.20 | 16512 | 3613 | 0 |
| lun10 | 3.20 | 16511 | 3613 | 0 |
| lun6 | 3.20 | 16475 | 3613 | 0 |
| lun14 | 3.20 | 16472 | 3613 | 0 |
| lun2 | 3.20 | 16457 | 3614 | 0 |
| lun22 | 3.20 | 16457 | 3613 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.90 | 14578 | 3615 | 0 |
| lun1 | 2.95 | 14937 | 3615 | 0 |
| lun16 | 2.96 | 14964 | 3615 | 0 |
| lun9 | 2.97 | 15060 | 3614 | 0 |
| lun20 | 2.98 | 15105 | 3615 | 0 |
| lun12 | 2.99 | 15145 | 3615 | 0 |
| lun5 | 3.00 | 15204 | 3615 | 0 |
| lun24 | 3.00 | 15244 | 3615 | 0 |
| lun8 | 3.04 | 15504 | 3615 | 0 |
| lun13 | 3.04 | 15509 | 3614 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.28 | 16828 |
| lun11 | 3.27 | 16753 |
| lun17 | 3.25 | 16662 |
| lun23 | 3.24 | 16578 |
| lun15 | 3.22 | 16512 |
| lun10 | 3.22 | 16511 |
| lun6 | 3.22 | 16475 |
| lun14 | 3.21 | 16472 |
| lun2 | 3.21 | 16457 |
| lun22 | 3.21 | 16457 |

## Snapshot 7: online_reads=350000, max_pending=16

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 465644 | 465643 | 1 | 0 | 16 | 1951064 | 573870 | 115644 | 223871 | 241773 | 108227 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@4@3@HIGH | 10602 | 10602 | 0 | 0.00 | 2 | 0.00 | 0 | 160 |
| User_Read_TR_Queue@5@0@HIGH | 10733 | 10733 | 0 | 0.00 | 1 | 0.00 | 0 | 104 |
| User_Read_TR_Queue@0@1@HIGH | 10712 | 10712 | 0 | 0.00 | 1 | 0.00 | 0 | 100 |
| User_Read_TR_Queue@0@2@HIGH | 10941 | 10941 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@2@3@HIGH | 11276 | 11276 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@2@1@HIGH | 10680 | 10680 | 0 | 0.00 | 1 | 0.00 | 0 | 94 |
| User_Read_TR_Queue@6@3@HIGH | 10930 | 10930 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@0@0@HIGH | 10837 | 10837 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@1@3@HIGH | 11327 | 11327 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@2@HIGH | 11043 | 11043 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.37 | 12.60 | 689514 |  |
| lun distribution | 3.12 | 2.92 | 3.25 | 689514 |  |
| read channel distribution | 12.50 | 12.34 | 12.62 |  | 573870 |
| read lun distribution | 3.12 | 2.87 | 3.27 |  | 573870 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.25 | 18774 | 3613 | 0 |
| lun17 | 3.23 | 18679 | 3614 | 0 |
| lun11 | 3.23 | 18657 | 3613 | 0 |
| lun23 | 3.21 | 18533 | 3613 | 0 |
| lun15 | 3.20 | 18437 | 3613 | 0 |
| lun10 | 3.20 | 18419 | 3613 | 0 |
| lun6 | 3.19 | 18414 | 3613 | 0 |
| lun2 | 3.19 | 18411 | 3614 | 0 |
| lun22 | 3.19 | 18394 | 3613 | 0 |
| lun14 | 3.19 | 18383 | 3613 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.92 | 16489 | 3615 | 0 |
| lun1 | 2.97 | 16844 | 3615 | 0 |
| lun16 | 2.97 | 16864 | 3615 | 0 |
| lun9 | 2.99 | 16987 | 3614 | 0 |
| lun20 | 2.99 | 17019 | 3615 | 0 |
| lun12 | 3.00 | 17052 | 3615 | 0 |
| lun24 | 3.02 | 17182 | 3615 | 0 |
| lun5 | 3.02 | 17197 | 3615 | 0 |
| lun8 | 3.05 | 17423 | 3615 | 0 |
| lun13 | 3.05 | 17442 | 3614 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.27 | 18774 |
| lun17 | 3.25 | 18679 |
| lun11 | 3.25 | 18657 |
| lun23 | 3.23 | 18533 |
| lun15 | 3.21 | 18437 |
| lun10 | 3.21 | 18419 |
| lun6 | 3.21 | 18414 |
| lun2 | 3.21 | 18411 |
| lun22 | 3.21 | 18394 |
| lun14 | 3.20 | 18383 |

## Snapshot 8: online_reads=400000, max_pending=16

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 515644 | 515643 | 1 | 0 | 16 | 2100872 | 623870 | 115644 | 223871 | 291773 | 108227 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@4@3@HIGH | 12137 | 12137 | 0 | 0.00 | 2 | 0.00 | 0 | 160 |
| User_Read_TR_Queue@5@0@HIGH | 12246 | 12246 | 0 | 0.00 | 1 | 0.00 | 0 | 104 |
| User_Read_TR_Queue@0@1@HIGH | 12217 | 12217 | 0 | 0.00 | 1 | 0.00 | 0 | 100 |
| User_Read_TR_Queue@0@2@HIGH | 12485 | 12485 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@2@3@HIGH | 12897 | 12897 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@2@1@HIGH | 12177 | 12177 | 0 | 0.00 | 1 | 0.00 | 0 | 94 |
| User_Read_TR_Queue@1@3@HIGH | 12965 | 12965 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@0@0@HIGH | 12367 | 12367 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@2@HIGH | 12603 | 12603 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@1@HIGH | 12475 | 12475 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.37 | 12.61 | 739514 |  |
| lun distribution | 3.12 | 2.92 | 3.25 | 739514 |  |
| read channel distribution | 12.50 | 12.34 | 12.63 |  | 623870 |
| read lun distribution | 3.12 | 2.89 | 3.27 |  | 623870 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.25 | 20412 | 3613 | 0 |
| lun11 | 3.23 | 20278 | 3613 | 0 |
| lun17 | 3.23 | 20273 | 3614 | 0 |
| lun23 | 3.21 | 20149 | 3613 | 0 |
| lun15 | 3.20 | 20070 | 3613 | 0 |
| lun10 | 3.19 | 20005 | 3613 | 0 |
| lun6 | 3.19 | 19997 | 3613 | 0 |
| lun22 | 3.19 | 19997 | 3613 | 0 |
| lun14 | 3.19 | 19964 | 3613 | 0 |
| lun2 | 3.19 | 19955 | 3614 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.92 | 18004 | 3615 | 0 |
| lun1 | 2.97 | 18349 | 3615 | 0 |
| lun16 | 2.98 | 18400 | 3615 | 0 |
| lun9 | 2.99 | 18484 | 3614 | 0 |
| lun20 | 2.99 | 18532 | 3615 | 0 |
| lun12 | 3.00 | 18591 | 3615 | 0 |
| lun5 | 3.03 | 18759 | 3615 | 0 |
| lun24 | 3.03 | 18766 | 3615 | 0 |
| lun8 | 3.05 | 18976 | 3615 | 0 |
| lun13 | 3.06 | 19048 | 3614 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.27 | 20412 |
| lun11 | 3.25 | 20278 |
| lun17 | 3.25 | 20273 |
| lun23 | 3.23 | 20149 |
| lun15 | 3.22 | 20070 |
| lun10 | 3.21 | 20005 |
| lun6 | 3.21 | 19997 |
| lun22 | 3.21 | 19997 |
| lun14 | 3.20 | 19964 |
| lun2 | 3.20 | 19955 |

## Snapshot 9: online_reads=450000, max_pending=16

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 565644 | 565643 | 1 | 0 | 16 | 2250731 | 673870 | 115644 | 223871 | 341773 | 108227 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@4@3@HIGH | 13652 | 13652 | 0 | 0.00 | 2 | 0.00 | 0 | 160 |
| User_Read_TR_Queue@5@0@HIGH | 13786 | 13786 | 0 | 0.00 | 1 | 0.00 | 0 | 104 |
| User_Read_TR_Queue@0@1@HIGH | 13765 | 13765 | 0 | 0.00 | 1 | 0.00 | 0 | 100 |
| User_Read_TR_Queue@0@2@HIGH | 14060 | 14060 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@2@3@HIGH | 14554 | 14554 | 0 | 0.00 | 1 | 0.00 | 0 | 99 |
| User_Read_TR_Queue@2@1@HIGH | 13692 | 13692 | 0 | 0.00 | 1 | 0.00 | 0 | 94 |
| User_Read_TR_Queue@1@3@HIGH | 14540 | 14540 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@0@0@HIGH | 13923 | 13923 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@2@HIGH | 14178 | 14178 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |
| User_Read_TR_Queue@6@1@HIGH | 14007 | 14007 | 0 | 0.00 | 1 | 0.00 | 0 | 87 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.38 | 12.59 | 789514 |  |
| lun distribution | 3.12 | 2.94 | 3.24 | 789514 |  |
| read channel distribution | 12.50 | 12.36 | 12.61 |  | 673870 |
| read lun distribution | 3.12 | 2.91 | 3.26 |  | 673870 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.24 | 21987 | 3613 | 0 |
| lun17 | 3.24 | 21937 | 3614 | 0 |
| lun11 | 3.24 | 21935 | 3613 | 0 |
| lun23 | 3.20 | 21673 | 3613 | 0 |
| lun15 | 3.20 | 21661 | 3613 | 0 |
| lun22 | 3.19 | 21572 | 3613 | 0 |
| lun6 | 3.19 | 21564 | 3613 | 0 |
| lun10 | 3.19 | 21553 | 3613 | 0 |
| lun2 | 3.18 | 21530 | 3614 | 0 |
| lun14 | 3.18 | 21525 | 3613 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.94 | 19614 | 3615 | 0 |
| lun16 | 2.98 | 19894 | 3615 | 0 |
| lun1 | 2.98 | 19897 | 3615 | 0 |
| lun9 | 2.99 | 19999 | 3614 | 0 |
| lun20 | 3.00 | 20072 | 3615 | 0 |
| lun12 | 3.01 | 20121 | 3615 | 0 |
| lun5 | 3.02 | 20266 | 3615 | 0 |
| lun24 | 3.03 | 20288 | 3615 | 0 |
| lun8 | 3.06 | 20583 | 3615 | 0 |
| lun13 | 3.07 | 20657 | 3614 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.26 | 21987 |
| lun17 | 3.26 | 21937 |
| lun11 | 3.26 | 21935 |
| lun23 | 3.22 | 21673 |
| lun15 | 3.21 | 21661 |
| lun22 | 3.20 | 21572 |
| lun6 | 3.20 | 21564 |
| lun10 | 3.20 | 21553 |
| lun2 | 3.19 | 21530 |
| lun14 | 3.19 | 21525 |

## Snapshot 10: online_reads=500000, max_pending=32

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 615644 | 615643 | 1 | 0 | 32 | 2413453 | 728366 | 115644 | 228367 | 387277 | 112723 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@4@3@HIGH | 15144 | 15144 | 0 | 0.00 | 3 | 0.00 | 0 | 243 |
| User_Read_TR_Queue@0@2@HIGH | 15640 | 15640 | 0 | 0.00 | 3 | 0.00 | 0 | 224 |
| User_Read_TR_Queue@1@2@HIGH | 15779 | 15779 | 0 | 0.00 | 3 | 0.00 | 0 | 220 |
| User_Read_TR_Queue@2@3@HIGH | 16057 | 16057 | 0 | 0.00 | 2 | 0.00 | 0 | 175 |
| User_Read_TR_Queue@0@3@HIGH | 15651 | 15651 | 0 | 0.00 | 2 | 0.00 | 0 | 160 |
| User_Read_TR_Queue@0@1@HIGH | 15302 | 15302 | 0 | 0.00 | 2 | 0.00 | 0 | 155 |
| User_Read_TR_Queue@1@3@HIGH | 16124 | 16124 | 0 | 0.00 | 2 | 0.00 | 0 | 141 |
| User_Read_TR_Queue@7@0@HIGH | 15498 | 15498 | 0 | 0.00 | 2 | 0.00 | 0 | 124 |
| User_Read_TR_Queue@2@1@HIGH | 15236 | 15236 | 0 | 0.00 | 2 | 0.00 | 0 | 119 |
| User_Read_TR_Queue@5@0@HIGH | 15337 | 15337 | 0 | 0.00 | 1 | 0.00 | 0 | 104 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.39 | 12.59 | 844010 |  |
| lun distribution | 3.12 | 2.95 | 3.24 | 844010 |  |
| read channel distribution | 12.50 | 12.37 | 12.60 |  | 728366 |
| read lun distribution | 3.12 | 2.92 | 3.26 |  | 728366 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun17 | 3.24 | 23715 | 3614 | 0 |
| lun7 | 3.24 | 23700 | 3613 | 0 |
| lun11 | 3.22 | 23583 | 3613 | 0 |
| lun23 | 3.20 | 23390 | 3613 | 0 |
| lun15 | 3.19 | 23327 | 3613 | 0 |
| lun6 | 3.19 | 23315 | 3613 | 0 |
| lun10 | 3.19 | 23305 | 3613 | 0 |
| lun22 | 3.19 | 23295 | 3613 | 0 |
| lun2 | 3.18 | 23245 | 3614 | 0 |
| lun14 | 3.18 | 23240 | 3613 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.95 | 21301 | 3615 | 0 |
| lun16 | 2.98 | 21572 | 3615 | 0 |
| lun1 | 2.99 | 21581 | 3615 | 0 |
| lun9 | 3.00 | 21677 | 3614 | 0 |
| lun12 | 3.01 | 21756 | 3615 | 0 |
| lun20 | 3.01 | 21757 | 3615 | 0 |
| lun5 | 3.03 | 21979 | 3615 | 0 |
| lun24 | 3.03 | 21986 | 3615 | 0 |
| lun8 | 3.07 | 22316 | 3615 | 0 |
| lun13 | 3.08 | 22349 | 3614 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun17 | 3.26 | 23715 |
| lun7 | 3.25 | 23700 |
| lun11 | 3.24 | 23583 |
| lun23 | 3.21 | 23390 |
| lun15 | 3.20 | 23327 |
| lun6 | 3.20 | 23315 |
| lun10 | 3.20 | 23305 |
| lun22 | 3.20 | 23295 |
| lun2 | 3.19 | 23245 |
| lun14 | 3.19 | 23240 |

## Snapshot 11: online_reads=550000, max_pending=32

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 665644 | 665643 | 1 | 0 | 32 | 2562280 | 778366 | 115644 | 228367 | 437277 | 112723 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@4@3@HIGH | 16674 | 16674 | 0 | 0.00 | 3 | 0.00 | 0 | 243 |
| User_Read_TR_Queue@0@2@HIGH | 17176 | 17176 | 0 | 0.00 | 3 | 0.00 | 0 | 224 |
| User_Read_TR_Queue@1@2@HIGH | 17341 | 17341 | 0 | 0.00 | 3 | 0.00 | 0 | 220 |
| User_Read_TR_Queue@2@3@HIGH | 17726 | 17726 | 0 | 0.00 | 2 | 0.00 | 0 | 175 |
| User_Read_TR_Queue@0@3@HIGH | 17156 | 17156 | 0 | 0.00 | 2 | 0.00 | 0 | 160 |
| User_Read_TR_Queue@0@1@HIGH | 16795 | 16795 | 0 | 0.00 | 2 | 0.00 | 0 | 155 |
| User_Read_TR_Queue@1@3@HIGH | 17750 | 17750 | 0 | 0.00 | 2 | 0.00 | 0 | 141 |
| User_Read_TR_Queue@7@0@HIGH | 17011 | 17011 | 0 | 0.00 | 2 | 0.00 | 0 | 124 |
| User_Read_TR_Queue@2@1@HIGH | 16733 | 16733 | 0 | 0.00 | 2 | 0.00 | 0 | 119 |
| User_Read_TR_Queue@5@0@HIGH | 16837 | 16837 | 0 | 0.00 | 1 | 0.00 | 0 | 104 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.38 | 12.59 | 894010 |  |
| lun distribution | 3.12 | 2.96 | 3.24 | 894010 |  |
| read channel distribution | 12.50 | 12.36 | 12.60 |  | 778366 |
| read lun distribution | 3.12 | 2.93 | 3.25 |  | 778366 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun7 | 3.24 | 25326 | 3613 | 0 |
| lun17 | 3.24 | 25324 | 3614 | 0 |
| lun11 | 3.23 | 25252 | 3613 | 0 |
| lun23 | 3.20 | 24987 | 3613 | 0 |
| lun15 | 3.20 | 24984 | 3613 | 0 |
| lun22 | 3.19 | 24915 | 3613 | 0 |
| lun10 | 3.19 | 24882 | 3613 | 0 |
| lun6 | 3.19 | 24878 | 3613 | 0 |
| lun14 | 3.18 | 24826 | 3613 | 0 |
| lun2 | 3.18 | 24781 | 3614 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.96 | 22814 | 3615 | 0 |
| lun1 | 2.99 | 23074 | 3615 | 0 |
| lun16 | 2.99 | 23112 | 3615 | 0 |
| lun9 | 3.00 | 23174 | 3614 | 0 |
| lun20 | 3.01 | 23257 | 3615 | 0 |
| lun12 | 3.01 | 23306 | 3615 | 0 |
| lun5 | 3.04 | 23538 | 3615 | 0 |
| lun24 | 3.04 | 23551 | 3615 | 0 |
| lun8 | 3.08 | 23894 | 3615 | 0 |
| lun13 | 3.08 | 23961 | 3614 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun7 | 3.25 | 25326 |
| lun17 | 3.25 | 25324 |
| lun11 | 3.24 | 25252 |
| lun23 | 3.21 | 24987 |
| lun15 | 3.21 | 24984 |
| lun22 | 3.20 | 24915 |
| lun10 | 3.20 | 24882 |
| lun6 | 3.20 | 24878 |
| lun14 | 3.19 | 24826 |
| lun2 | 3.18 | 24781 |

## Snapshot 12: online_reads=600000, max_pending=32

### Online / mapping summary

| requests | completed | pending | completed_queue | max_pending | events_run | flash_reads | flash_writes | mapping_reads | cmt_read_hits | cmt_read_misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 715644 | 715643 | 1 | 0 | 32 | 2712088 | 828366 | 115644 | 228367 | 487277 | 112723 |

### Top internal queues by max wait

| Queue | Enqueued | Dequeued | CurLen | AvgQLen | MaxQLen | StdQLen | AvgWait(us) | MaxWait(us) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User_Read_TR_Queue@4@3@HIGH | 18200 | 18200 | 0 | 0.00 | 3 | 0.00 | 0 | 243 |
| User_Read_TR_Queue@0@2@HIGH | 18780 | 18780 | 0 | 0.00 | 3 | 0.00 | 0 | 224 |
| User_Read_TR_Queue@1@2@HIGH | 18932 | 18932 | 0 | 0.00 | 3 | 0.00 | 0 | 220 |
| User_Read_TR_Queue@2@3@HIGH | 19357 | 19357 | 0 | 0.00 | 2 | 0.00 | 0 | 175 |
| User_Read_TR_Queue@0@3@HIGH | 18732 | 18732 | 0 | 0.00 | 2 | 0.00 | 0 | 160 |
| User_Read_TR_Queue@0@1@HIGH | 18369 | 18369 | 0 | 0.00 | 2 | 0.00 | 0 | 155 |
| User_Read_TR_Queue@1@3@HIGH | 19332 | 19332 | 0 | 0.00 | 2 | 0.00 | 0 | 141 |
| User_Read_TR_Queue@7@0@HIGH | 18603 | 18603 | 0 | 0.00 | 2 | 0.00 | 0 | 124 |
| User_Read_TR_Queue@2@1@HIGH | 18271 | 18271 | 0 | 0.00 | 2 | 0.00 | 0 | 119 |
| User_Read_TR_Queue@5@0@HIGH | 18404 | 18404 | 0 | 0.00 | 1 | 0.00 | 0 | 104 |

### Distribution

| distribution | ideal_pct | min_pct | max_pct | total_ops | total_reads |
| --- | --- | --- | --- | --- | --- |
| channel distribution | 12.50 | 12.39 | 12.58 | 944010 |  |
| lun distribution | 3.12 | 2.97 | 3.24 | 944010 |  |
| read channel distribution | 12.50 | 12.38 | 12.59 |  | 828366 |
| read lun distribution | 3.12 | 2.95 | 3.26 |  | 828366 |

### hottest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun17 | 3.24 | 26970 | 3614 | 0 |
| lun7 | 3.23 | 26908 | 3613 | 0 |
| lun11 | 3.23 | 26883 | 3613 | 0 |
| lun15 | 3.19 | 26540 | 3613 | 0 |
| lun23 | 3.19 | 26507 | 3613 | 0 |
| lun6 | 3.19 | 26469 | 3613 | 0 |
| lun22 | 3.19 | 26467 | 3613 | 0 |
| lun10 | 3.19 | 26455 | 3613 | 0 |
| lun14 | 3.18 | 26389 | 3613 | 0 |
| lun2 | 3.18 | 26385 | 3614 | 0 |

### coldest luns

| lun | pct | reads | writes | erases |
| --- | --- | --- | --- | --- |
| lun28 | 2.97 | 24406 | 3615 | 0 |
| lun16 | 2.99 | 24592 | 3615 | 0 |
| lun1 | 2.99 | 24648 | 3615 | 0 |
| lun9 | 3.00 | 24712 | 3614 | 0 |
| lun20 | 3.01 | 24824 | 3615 | 0 |
| lun12 | 3.01 | 24825 | 3615 | 0 |
| lun5 | 3.04 | 25067 | 3615 | 0 |
| lun24 | 3.04 | 25093 | 3615 | 0 |
| lun8 | 3.08 | 25498 | 3615 | 0 |
| lun13 | 3.09 | 25542 | 3614 | 0 |

### hottest read luns

| lun | pct | reads |
| --- | --- | --- |
| lun17 | 3.26 | 26970 |
| lun7 | 3.25 | 26908 |
| lun11 | 3.25 | 26883 |
| lun15 | 3.20 | 26540 |
| lun23 | 3.20 | 26507 |
| lun6 | 3.20 | 26469 |
| lun22 | 3.20 | 26467 |
| lun10 | 3.19 | 26455 |
| lun14 | 3.19 | 26389 |
| lun2 | 3.19 | 26385 |

