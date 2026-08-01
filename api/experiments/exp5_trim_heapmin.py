"""实验5: 让日志输出"稳定后"内存的可行方法

验证:
A. msvcrt._heapmin() 强制 CRT 堆归还空闲块（真正释放 commit）
B. 修剪工作集 + 触达模型参数（模拟真实稳定态的工作集）
"""
import ctypes
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

import psutil
import torch

from funasr import AutoModel

proc = psutil.Process(os.getpid())
MODEL_DIR = r"D:/Projects/phonetics-2/models/SenseVoiceSmall"


def rss():
    return proc.memory_info().rss / 1024 / 1024


def commit():
    return proc.memory_info().vms / 1024 / 1024


def heapmin():
    # Python 3.12 使用 UCRT (ucrtbase.dll)，老 msvcrt.dll 的堆不归 PyTorch 管理
    try:
        ctypes.CDLL("ucrtbase.dll")._heapmin()
    except Exception:
        ctypes.CDLL("msvcrt.dll")._heapmin()


def trim_working_set():
    if sys.platform == "win32":
        k32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)
        h = k32.GetCurrentProcess()
        k32.SetProcessWorkingSetSize(ctypes.c_void_p(h), ctypes.c_size_t(-1), ctypes.c_size_t(-1))


def touch_params(model):
    """读取全部参数触发换入，模拟首次推理后的活跃集。"""
    total = torch.tensor(0.0, dtype=torch.float32)
    for p in model.parameters():
        total = total + p.detach().sum()


print(f"STEP0 baseline           RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)

model = AutoModel(model=MODEL_DIR, device="cpu", disable_update=True)
print(f"STEP1 loaded (峰值)      RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)

# 方案 A: _heapmin 强制堆归还
heapmin()
time.sleep(0.5)
print(f"STEP2 _heapmin() 后      RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)

# 方案 B: 修剪工作集 + 触达参数
trim_working_set()
time.sleep(0.3)
print(f"STEP3 修剪工作集后       RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)
touch_params(model)
time.sleep(0.3)
print(f"STEP4 触达参数后(稳定态) RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)

# 验证模型仍可用
import torchaudio
print(f"STEP5 模型对象存活       RSS={rss():6.0f}MB  commit={commit():6.0f}MB", flush=True)
