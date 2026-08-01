# SenseVoice 模型内存占用 3GB 问题 — 实验报告

日期: 2026-08-01
环境: Windows 11 / Python 3.12.12 / torch 2.10.0+cpu / funasr 1.3.1 / psutil 7.2.2

## 摘要

日志中 `内存=356MB→3066MB | 增量=+2704MB` 的数字是真实、准确的（与任务管理器口径一致，已三重交叉验证），但它描述的是进程工作集（Working Set）的峰值，其中约 1.8GB 是 FunASR 加载流程制造的冗余拷贝，加载结束后因 PyTorch CPU 分配器不归还内存而残留在 RSS 中。

结论: 这是 FunASR `load_pretrained_model` 中一行多余的 `copy.deepcopy` 引起的，同时被 PyTorch CPU 分配器的缓存行为放大。去掉该 deepcopy 后，加载完成内存从 3053MB 降到 2159MB（省 ~895MB）。

## 目录

- 1. 模型基本信息
- 2. 现象与日志口径
- 3. 实验一: 原生加载基线（模型本身该占多少）
- 4. 实验二: 当前工程加载全流程分阶段测量
- 5. 实验三: 内存统计方式验证
- 6. 补充实验: fp16 的影响
- 7. 根因分析
- 8. 为什么"之前只有 1G 多"
- 9. 补充观察: Windows 工作集被修剪，但 commit 不降
- 10. 统计方式评价
- 11. 优化建议
- 12. 复现方法

## 1. 模型基本信息

模型: SenseVoiceSmall（50 层 encoder + 20 层 tp_blocks，来自 ModelScope iic/SenseVoiceSmall）

| 项目 | 数值 |
|---|---|
| 模型文件 model.pt | 892.92 MB |
| 参数量 | 234.00M (float32) |
| 参数张量字节 | 892.64 MB |
| state_dict 键数 | 917 |

参数量 × 4 字节与文件大小完全吻合，说明模型权重本身就是约 893MB，float32 无压缩。

## 2. 现象与日志口径

工程日志（[sensevoice.py](../src/services/sensevoice.py) 的 get_model）:

```
[sensevoice] 模型加载完成 | 耗时=1.92s | 内存=356MB→3066MB | 增量=+2710MB
```

用户反馈: 任务管理器（资源管理器）实际显示的占用与日志一致，约 3GB。而此前使用记忆是"1G 多一点"。

## 3. 实验一: 原生加载基线（模型本身该占多少）

脚本: [exp1_native_load.py](../experiments/exp1_native_load.py)

直接使用 PyTorch 原生 `torch.load` 加载权重（等效于 FunASR 内部 `ori_state` 那一步）:

```
[0] import torch/funasr/torchaudio 基线          RSS=  350MB
[1] torch.load 权重 (耗时 0.46s)                 RSS= 1245MB  Δ=+895MB
[2] del + gc.collect() 后                       RSS= 1244MB  （不回落）
[3] 再分配 234M float32 (892MB) 张量             RSS= 1244MB  （不涨）
```

结论:
- 模型权重本身只需要约 895MB。
- 权重释放后 RSS 不回落（第 2 步），说明 PyTorch CPU 分配器把这 895MB 缓存在进程内，不归还操作系统。
- 再次分配 892MB 张量时 RSS 不涨（第 3 步），证明缓存可以被复用，这部分内存并非"泄漏"，而是"可复用的滞留内存"。

即: 一次干净的加载（只有模型参数），稳定内存应为 350 + 893 ≈ 1250MB（1.25GB），与用户"1G 多"的记忆吻合。

## 4. 实验二: 当前工程加载全流程分阶段测量

脚本: [exp2_funasr_stages.py](../experiments/exp2_funasr_stages.py)（带打点的 load_pretrained_model，两个模式分别独立进程运行）

### 4A. 含 deepcopy（当前工程原状，复现 3GB）

```
[0] import 基线                                      RSS=  349MB
  [probe] obj.state_dict() 视图（无分配）               RSS= 1252MB  （模型实例参数已分配）
  [probe] torch.load 完成 (+权重1)                    RSS= 2149MB  Δ=+897MB
  [probe] copy.deepcopy 完成 (+权重2)                 RSS= 3044MB  Δ=+1792MB
  [probe] load_state_dict 完成                       RSS= 3044MB
[1] AutoModel 构建完成 (耗时 1.69s)                    RSS= 3053MB  Δ=+2704MB
[2] del model + gc.collect() 后                     RSS= 3018MB  （基本不回落）
```

### 4B. 去掉 deepcopy（隔离其贡献）

```
[0] import 基线                                      RSS=  349MB
  [probe] obj.state_dict() 视图                        RSS= 1253MB
  [probe] torch.load 完成 (+权重1)                    RSS= 2149MB  Δ=+897MB
  [probe] 无 deepcopy（直接复用 ori_state）            RSS= 2149MB
  [probe] load_state_dict 完成                       RSS= 2150MB
[1] AutoModel 构建完成 (耗时 1.36s)                    RSS= 2159MB  Δ=+1810MB
[2] del model + gc.collect() 后                     RSS= 2124MB
```

对照表:

| 阶段 | 含 deepcopy | 去 deepcopy | 差值 |
|---|---|---|---|
| 模型实例参数 | +903MB | +904MB | — |
| torch.load 权重 | +897MB | +897MB | — |
| deepcopy 权重 | +895MB | 0 | 895MB |
| 加载完成 RSS | 3053MB | 2159MB | 895MB |
| 增量 | +2704MB | +1810MB | 895MB |

deepcopy 贡献了整整一份 895MB 的权重拷贝，与日志增量 +2704MB 完全对应。

## 5. 实验三: 内存统计方式验证

脚本: [exp3_stats_check.py](../experiments/exp3_stats_check.py)

同一进程同时用 psutil、Windows API（GetProcessMemoryInfo）、tasklist 三种方式统计:

| 阶段 | psutil.rss | WinAPI WorkingSetSize | tasklist 内存使用 |
|---|---|---|---|
| import 基线 | 350 MB | 350 MB | — |
| AutoModel 加载后 | 3055 MB | 3055 MB | 3,092,276 K ≈ 3020 MB |
| del + gc 后 | 3020 MB | 3020 MB | — |
| 再分配 892MB 张量后 | 3020 MB | 3020 MB | — |

同时对比私有提交内存（PrivateUsage == psutil.vms == PagefileUsage）:

| 阶段 | WorkingSetSize | PrivateUsage |
|---|---|---|
| AutoModel 加载后 | 3055 MB | 4567 MB |
| del + gc 后 | 3020 MB | 4530 MB |
| 再分配 892MB 张量后 | 3020 MB | 5432 MB |

结论:
- psutil.rss 在 Windows 上就是进程的工作集（Working Set），与任务管理器"内存"列完全一致。工程日志的统计口径没有错。
- del 模型后工作集基本不回落（3054→3020MB），证明滞留的 ~2.1GB 里包含大量分配器缓存。
- 再分配 892MB 时工作集不变、提交内存 +900MB: 说明 PyTorch 分配器直接复用了滞留的物理页（工作集不涨），只消耗新的虚拟地址空间。滞留内存确实可复用，不是泄漏，但对操作系统而言仍被该进程占据。

## 6. 补充实验: fp16 的影响

```
STEP0 baseline           349MB
STEP1 torch.load fp32    1244MB  Δ=+895MB
STEP2 保留 fp32+fp16     1693MB  Δ=+1344MB
STEP3 仅留 fp16          1692MB  Δ=+1343MB
fp16 张量字节 446MB
```

fp16 使权重从 893MB 降到 446MB，但 fp32 版本释放后仍被分配器缓存，RSS 停在 1692MB。说明在 Windows 上仅靠 fp16 无法让 RSS 回落到理想值，需要叠加处理分配器缓存。

## 7. 根因分析

### 直接原因: FunASR `load_pretrained_model` 的多余深拷贝

文件: `.venv/Lib/site-packages/funasr/train_utils/load_pretrained_model.py`

```python
ori_state = torch.load(path, map_location="cpu")   # ① 权重1
src_state = copy.deepcopy(ori_state)                # ② 权重2（冗余）
src_state = src_state["state_dict"] if ...          # ③ model.pt 顶层就是平铺 state_dict，无嵌套
```

调用链:
1. AutoModel 加载本地目录时，`download_model_from_hub.py` 把 `init_param` 指向 `model.pt`。
2. `build_model` 先实例化 `SenseVoiceSmall`（分配 893MB 随机参数）。
3. `load_pretrained_model` 里 `torch.load` 再读一份 893MB。
4. `copy.deepcopy` 又复制一份 893MB，而这完全没必要: model.pt 顶层就是平铺的 state_dict，`"state_dict"/"model_state_dict"/"model"` 三个嵌套检查都不会命中，deepcopy 出的 `src_state` 与 `ori_state` 内容完全相同。

加载过程中三份权重（模型参数 + ori_state + src_state）同时存在:

```
3053MB ≈ 349 基线 + 893 模型参数 + 893 torch.load + 893 deepcopy + ~25MB 组件
```

### 放大原因: PyTorch CPU 分配器不归还内存给操作系统

- `load_pretrained_model` 返回后 `ori_state` / `src_state` 引用计数归零，对象被释放。
- 但 torch 的 CPU 分配器（`c10::alloc_cpu`）把释放的内存块缓存在进程内，不归还 OS；Windows CRT 堆也不主动归还大块。
- 因此 RSS 停留在历史峰值 ~3GB，任务管理器显示 3GB 是真实的工作集。

这与 PyTorch CUDA 的缓存分配器是同一套设计哲学（为了避免反复向系统申请内存的代价），只是 CPU 侧没有公开的 `empty_cache()`。

## 8. 为什么"之前只有 1G 多"

最可能的解释是运行平台差异，而非代码差异:

- 本项目历史中 funasr 依赖一直是 `>=1.3.1`，torch 一直是 `>=2.10.0`，模型加载路径没有改动过（见 git 历史）。
- `.env` 示例中模型路径是 Linux 风格（`/home/lcl/data/models/SenseVoiceSmall`），说明此前主要在 Linux/WSL 上运行。
- Linux 的 glibc malloc 对大于 128KB 的分配走 mmap，`free` 时直接 munmap 归还操作系统。torch.load 的 900MB 大块释放后 RSS 会真实回落，最终停在"基线 + 模型参数"≈ 1.25GB。
- Windows 的 CRT 堆不会归还大块，RSS 停在历史峰值 3GB。

验证方法: 在 Linux/WSL 上运行 [exp2_funasr_stages.py](../experiments/exp2_funasr_stages.py) deepcopy 模式，若 [2] del 后 RSS 回落到 ~1250MB，即证实该假设。

## 9. 补充观察: Windows 工作集被修剪，但 commit 不降

2026-08-02 在目标机器上复测加载模型后的实际进程（PID 42456）:

| 指标 | 数值 | 说明 |
|---|---|---|
| 工作集（任务管理器"内存"列） | 1340MB | Windows 已将滞留缓存页换出到页文件，物理驻留回落到"基线 + 模型参数"≈ 1.25GB |
| 提交大小（commit / pagefile usage） | 4750MB | 进程实际提交的虚拟内存配额，其中约 3GB 为模型加载相关（含 deepcopy + torch.load 缓存），其余 ~1.7GB 为 torch/MKL/运行时基线 |

要点:
- 任务管理器"内存"列显示的工作集会被 Windows 动态修剪，加载完成瞬间显示 3GB，运行稳定后被修剪到 ~1.3GB，所以资源管理器里看到 1.2GB 是真实的，但只是物理驻留部分。
- commit（提交大小，任务管理器中需手动添加该列）居高不下: 滞留的 1.8GB 缓存只是被换出，并未释放，进程仍占用约 4.7GB 的虚拟内存配额。
- 这解释了三种平台表象的统一图景: Linux/macOS 大块 malloc 释放后真实归还（commit 与工作集同降），Windows 工作集被修剪但 commit 保留。

## 10. 统计方式评价

工程日志的统计方式本身是正确的:
- psutil `Process(pid).memory_info().rss` 就是进程工作集，与任务管理器"内存"列同口径，本次已与 WinAPI、tasklist 三方交叉验证一致。
- 日志输出的是进程在工作集口径下的真实变化，并非统计错误。

需要注意的语义边界:
- RSS 是"物理驻留"口径，包含分配器缓存的、已释放但未归还 OS 的内存。3066MB 中约 1.8GB 属于这类滞留缓存。
- 若要表达"模型真正活跃占用的内存"，RSS 会高估；但进程对系统的真实占用确实是 RSS（滞留页其他进程无法使用）。
- 可选改进: 日志追加输出 `进程私有提交内存`（psutil.vms）或标注"工作集口径"，避免"3GB"被误解为模型本身的大小。

## 11. 优化建议

| 方案 | 收益 | 说明 |
|---|---|---|
| 去掉 FunASR deepcopy（monkey-patch 或提 PR） | 稳定内存 3053→2159MB，峰值省 895MB | 收益最直接；FunASR 上游 1.3.1 仍有此问题 |
| fp16 量化加载 | 权重 893→446MB | 需验证推理精度，配合分配器问题效果才完整 |
| Linux 上运行 | RSS 自然回落到 ~1.25GB | 平台 malloc 行为差异，非代码层面修复 |
| 接受现状 | — | 滞留内存可被进程内复用，不会持续增长；代价是任务管理器数字偏高 |

注意: 由于 PyTorch CPU 分配器缓存无法从应用层强制清空，在 Windows 上即使正确加载（去 deepcopy），RSS 也会停在 ~2159MB（含 torch.load 的一次性拷贝缓存）。要达到"1G 多"，需要同时去掉 deepcopy 且处理分配器缓存（如换 mimalloc，或在 Linux 上运行），或采用 fp16。

## 12. 复现方法

```bash
cd api
# 原生加载基线
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe experiments/exp1_native_load.py
# 当前工程分阶段（含 deepcopy）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe experiments/exp2_funasr_stages.py deepcopy
# 去掉 deepcopy 对照
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe experiments/exp2_funasr_stages.py nodeepcopy
# 统计口径验证
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe experiments/exp3_stats_check.py
```

## 附: 相关文件

- 加载代码: [src/services/sensevoice.py](../src/services/sensevoice.py)、[src/demo/sensevoice_demo.py](../src/demo/sensevoice_demo.py)
- 实验脚本: [experiments/](../experiments/)
- 原始分析（问题定位草稿）: [memory-analysis.md](./memory-analysis.md)
