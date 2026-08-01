"""实验3: 内存统计方式验证

对照 psutil.rss 与 Windows 任务管理器口径（working set / private bytes），
确认工程日志的统计方式是否正确，并量化"虚高"成分。
"""
import ctypes
import gc
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

import psutil
import torch

from funasr import AutoModel

proc = psutil.Process(os.getpid())
MODEL_DIR = r"D:/Projects/phonetics-2/models/SenseVoiceSmall"


def win_private_bytes():
    """通过 Windows API GetProcessMemoryInfo 获取 working set / private bytes。"""
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    psapi = ctypes.WinDLL("psapi.dll")
    k32 = ctypes.WinDLL("kernel32.dll")
    h = k32.GetCurrentProcess()
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    psapi.GetProcessMemoryInfo(ctypes.c_void_p(h), ctypes.byref(counters), counters.cb)
    return counters.WorkingSetSize, counters.PrivateUsage, counters.PagefileUsage


def dump(label):
    ws, priv, pf = win_private_bytes()
    p = psutil.Process(os.getpid())
    mi = p.memory_info()
    print(f"{label:46s}")
    print(f"    psutil.rss (working set)      = {mi.rss/1024/1024:8.0f} MB")
    print(f"    psutil.vms (virtual)          = {mi.vms/1024/1024:8.0f} MB")
    print(f"    WinAPI WorkingSetSize         = {ws/1024/1024:8.0f} MB")
    print(f"    WinAPI PrivateUsage (私有)     = {priv/1024/1024:8.0f} MB")
    print(f"    WinAPI PagefileUsage          = {pf/1024/1024:8.0f} MB")


print("=" * 80)
print("阶段 0: import 基线")
print("=" * 80)
dump("[0] import torch/funasr 后")

print()
print("=" * 80)
print("阶段 1: AutoModel 加载后（当前工程，应 ~3GB）")
print("=" * 80)
model = AutoModel(model=MODEL_DIR, device="cpu", disable_update=True)
dump("[1] AutoModel 加载后")

print()
print("=" * 80)
print("阶段 2: 释放模型 + gc 后")
print("=" * 80)
del model
gc.collect()
dump("[2] del + gc.collect() 后")

print()
print("=" * 80)
print("阶段 3: 再分配 892MB 张量（验证分配器缓存可复用性）")
print("=" * 80)
t = torch.empty(234_000_000, dtype=torch.float32)
dump("[3] 分配 892MB 新张量后")
del t
gc.collect()

print()
print("=" * 80)
print("对照: Windows tasklist 看到的进程条目")
print("=" * 80)
out = subprocess.run(
    ["tasklist", "/FI", f"PID eq {os.getpid()}", "/FO", "CSV"],
    capture_output=True,
    text=True,
).stdout
for line in out.strip().splitlines():
    print("   ", line)
