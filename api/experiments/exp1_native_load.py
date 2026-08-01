"""实验1: 原生方式加载 SenseVoice 模型权重，测量真实内存占用基线

回答: 模型本身（权重）到底应该占多少内存？释放后 RSS 是否回落？
"""
import gc
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

import psutil
import torch

# 与工程一致地导入这些库，模拟真实进程基线
from funasr import AutoModel  # noqa: F401
import torchaudio  # noqa: F401

proc = psutil.Process(os.getpid())
MODEL_PATH = r"D:/Projects/phonetics-2/models/SenseVoiceSmall/model.pt"


def rss():
    return proc.memory_info().rss / 1024 / 1024


def report(tag, base=None):
    cur = rss()
    d = "" if base is None else f"  Δ={cur - base:+.0f}MB"
    print(f"{tag:52s} RSS={cur:8.0f}MB{d}")
    return cur


base = report("[0] import torch/funasr/torchaudio 基线")

# ---- A1: 纯 torch.load 权重（等效于 funasr 内部 ori_state）----
t0 = time.time()
sd = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
dur = time.time() - t0
report(f"[1] torch.load 权重 (耗时 {dur:.2f}s)", base)

# 确认张量占用
total = sum(v.numel() * v.element_size() for v in sd.values())
print(f"    -> state_dict 张量实际字节: {total / 1024 / 1024:.1f} MB")

# ---- A2: 释放后 RSS 是否回落（验证 PyTorch CPU 分配器是否归还 OS）----
del sd
gc.collect()
time.sleep(0.3)
report("[2] del + gc.collect() 后", base)

# ---- A3: 分配器缓存验证：释放的内存能否被后续分配复用 ----
# 如果分配器缓存了 893MB，再分配一个 893MB 张量，RSS 不应大幅上涨
t = torch.empty(234_000_000, dtype=torch.float32)
report("[3] 再分配 234M float32 (892MB) 张量", base)
del t
gc.collect()
report("[4] 再释放后", base)

print("\n结论待汇总（写入实验报告）")
