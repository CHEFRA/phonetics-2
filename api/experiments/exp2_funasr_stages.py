"""实验2: 当前工程加载流程逐步测量内存

用带打点的 load_pretrained_model 替换 funasr 原版，在每一步打印 RSS，
复现工程日志中的 ~3GB 现象，并验证 deepcopy 的贡献、释放后是否回落。
"""
import copy
import gc
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

import psutil
import torch

from funasr import AutoModel
import funasr.auto.auto_model as am
import funasr.train_utils.load_pretrained_model as lpm

proc = psutil.Process(os.getpid())
MODEL_DIR = r"D:/Projects/phonetics-2/models/SenseVoiceSmall"


def rss():
    return proc.memory_info().rss / 1024 / 1024


def report(tag, base=None):
    cur = rss()
    d = "" if base is None else f"  Δ={cur - base:+.0f}MB"
    print(f"{tag:52s} RSS={cur:8.0f}MB{d}", flush=True)
    return cur


def make_probe(deepcopy_enabled=True):
    """复刻 funasr load_pretrained_model，带阶段内存打点。"""

    def load_pretrained_model_probe(
        path,
        model,
        ignore_init_mismatch=True,
        map_location="cpu",
        oss_bucket=None,
        scope_map=[],
        excludes=None,
        **kwargs,
    ):
        base = rss()
        obj = model
        dst_state = obj.state_dict()
        report("  [probe] obj.state_dict() 视图（无分配）", base)
        ori_state = torch.load(path, map_location=map_location)
        report("  [probe] torch.load 完成 (+权重1)", base)
        if deepcopy_enabled:
            src_state = copy.deepcopy(ori_state)
            report("  [probe] copy.deepcopy 完成 (+权重2)", base)
        else:
            src_state = ori_state
            report("  [probe] 无 deepcopy（直接复用 ori_state）", base)
        src_state = (
            src_state["state_dict"] if "state_dict" in src_state else src_state
        )
        src_state = (
            src_state["model_state_dict"]
            if "model_state_dict" in src_state
            else src_state
        )
        src_state = src_state["model"] if "model" in src_state else src_state
        scope_map = ["module.", "None"] if isinstance(scope_map, str) else scope_map + ["module.", "None"]
        for k in dst_state.keys():
            k_src = k
            if scope_map is not None:
                src_prefix = ""
                dst_prefix = ""
                for i in range(0, len(scope_map), 2):
                    src_prefix = scope_map[i] if str(scope_map[i]).lower() != "none" else ""
                    dst_prefix = scope_map[i + 1] if str(scope_map[i + 1]).lower() != "none" else ""
                    if dst_prefix == "" and (src_prefix + k) in src_state.keys():
                        k_src = src_prefix + k
                    elif k.startswith(dst_prefix) and k.replace(dst_prefix, src_prefix, 1) in src_state.keys():
                        k_src = k.replace(dst_prefix, src_prefix, 1)
            if k_src in src_state.keys():
                if ignore_init_mismatch and dst_state[k].shape != src_state[k_src].shape:
                    pass
                else:
                    dst_state[k] = src_state[k_src]
            else:
                print(f"Warning, miss key in ckpt: {k}")
        obj.load_state_dict(dst_state, strict=True)
        report("  [probe] load_state_dict 完成", base)

    return load_pretrained_model_probe


def run(deepcopy_enabled: bool, label: str):
    print("=" * 80)
    print(f"实验: {label}")
    print("=" * 80)
    base = report("[0] import 基线")
    # auto_model.py 用的是 `from ... import load_pretrained_model`，
    # 需同时 patch 两个名字才生效。
    lpm.load_pretrained_model = make_probe(deepcopy_enabled)
    am.load_pretrained_model = lpm.load_pretrained_model
    t0 = time.time()
    model = AutoModel(model=MODEL_DIR, device="cpu", disable_update=True)
    dur = time.time() - t0
    report(f"[1] AutoModel 构建完成 (耗时 {dur:.2f}s)", base)

    # 释放后是否回落
    del model
    gc.collect()
    time.sleep(0.3)
    report("[2] del model + gc.collect() 后", base)
    print()


# 通过命令行参数指定模式，避免分配器缓存污染对比（每组独立进程运行）
mode = sys.argv[1] if len(sys.argv) > 1 else "both"
if mode in ("deepcopy", "both"):
    run(deepcopy_enabled=True, label="A. 当前工程加载（含 deepcopy，应复现 ~3GB）")
if mode in ("nodeepcopy", "both"):
    run(deepcopy_enabled=False, label="B. 去掉 deepcopy 加载（隔离 deepcopy 贡献）")
