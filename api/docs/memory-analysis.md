# SenseVoice 模型内存占用分析

## 模型信息

- 模型格式: PyTorch (`model.pt`)
- 文件大小: 893 MB
- 模型架构: SenseVoiceSmall（50 层 encoder + 20 层 tp_blocks）
- 参数量约: 220M (float32)

## 内存实测数据

| 阶段 | RSS | 增量 |
|---|---|---|
| Python 基线（import 后） | ~350 MB | — |
| 模型创建（model_class） | ~1250 MB | +~900 MB |
| torch.load 权重 | ~2150 MB | +~900 MB |
| deepcopy 权重 | ~3050 MB | +~900 MB |
| 稳定后 | ~3054 MB | +~2704 MB |

> PyTorch CPU 分配器不会将释放的内存归还 OS，因此 RSS 保持在历史峰值。

## 根因: FunASR `load_pretrained_model` 多余的 `copy.deepcopy`

文件: `funasr/train_utils/load_pretrained_model.py`

```python
ori_state = torch.load(path, map_location="cpu")   # ① torch.load 900MB
src_state = copy.deepcopy(ori_state)                # ② 无意义深拷贝又 +900MB
```

`SenseVoiceSmall` 的 `model.pt` 直接保存的是平铺的 `state_dict`（无 `"state_dict"` / `"model"` 嵌套），`deepcopy` 完全是浪费。`ori_state` 本身已经可以直接用，不需要深拷贝。

## 内存堆栈

```
2704 MB ≈ 3 × 900 MB
  ├── 模型实例参数                         ~900 MB
  ├── torch.load 权重 (ori_state)          ~900 MB
  └── copy.deepcopy 权重 (src_state)       ~900 MB
```

- `torch.load` → `copy.deepcopy` 之间的时间窗内两份 `state_dict` 共存，峰值约 1800 MB
- 加上模型参数本身，峰值约 2700 MB
- `del` 后 PyTorch 分配器不归还 OS，RSS 不回落

## 优化方向

| 方案 | 收益 | 难度 | 备注 |
|---|---|---|---|
| Monkey-patch 去掉 deepcopy | 节省 ~900 MB 峰值 | 低 | 直接修改 load_pretrained_model 行为 |
| 提交 PR 给 FunASR 修复 | 社区受益 | 中 | 需确认 deepcopy 的设计意图 |
| 模型量化 (fp16/int8) | 参数内存减半以上 | 中 | 需验证推理精度 |
| 使用 ONNX 导出 | 减少运行时开销 | 高 | 需额外导出步骤 |

## 验证方法

```bash
# 模型加载内存监控（已集成到 service 和 demo）
cd api && uv run python -c "
from src.core.asr_registry import get_asr_service
get_asr_service().get_model()
"

# 预期输出:
# [sensevoice] 模型加载完成 | 耗时=1.43s | 内存=350MB→3054MB | 增量=+2704MB
```
