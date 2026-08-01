"""实验4: 如何让日志输出"稳定后"的内存占用

验证两种方案:
A. 加载后 sleep 等待 Windows 自然修剪工作集
B. 主动调用 SetProcessWorkingSetSize 修剪工作集
"""
import ctypes
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

import psutil

from funasr import AutoModel

proc = psutil.Process(os.getpid())
MODEL_DIR = r"D:/Projects/phonetics-2/models/SenseVoiceSmall"


def rss():
    return proc.memory_info().rss / 1024 / 1024


def commit():
    return proc.memory_info().vms / 1024 / 1024


print(f"STEP0 baseline           RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)

model = AutoModel(model=MODEL_DIR, device="cpu", disable_update=True)
print(f"STEP1 loaded (峰值)      RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)

# 方案 A: 等待自然修剪
time.sleep(10)
print(f"STEP2 sleep 10s 后       RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)

# 方案 B: 主动修剪工作集
if sys.platform == "win32":
    k32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)
    h = k32.GetCurrentProcess()
    k32.SetProcessWorkingSetSize(ctypes.c_void_p(h), ctypes.c_size_t(-1), ctypes.c_size_t(-1))
time.sleep(1)
print(f"STEP3 主动修剪工作集后    RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)

# 触达一次模型，看工作集是否回到活跃值（模拟首次推理）
import torch
with torch.no_grad():
    x = torch.randn(1, 1, 80, 100)  # 只是分配 CPU 张量触达内存路径
print(f"STEP4 分配张量后         RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)
