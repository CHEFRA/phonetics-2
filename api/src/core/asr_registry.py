"""ASR 引擎注册表

统一入口 get_asr_service() 返回当前引擎的服务单例，桌面端、API、demo
都从这里取服务，不再直接 import 具体服务。模型保持懒加载：
set_active_model()/set_model_dir() 只替换单例，不加载模型。
"""

from src.core import config
from src.core.config import ASR_MODEL, MODEL_DIR, STREAMING_MODEL_DIR
from src.services.sensevoice import SenseVoiceService
from src.services.streaming_paraformer import StreamingParaformerService


class ASRSpec:
    """一个 ASR 引擎的注册信息"""

    def __init__(self, name, service_cls, model_id, mode):
        self.name = name
        self.service_cls = service_cls
        self.model_id = model_id
        self.mode = mode  # batch（整段）/ stream（流式）


_SPECS = {
    "sensevoice": ASRSpec(
        name="sensevoice",
        service_cls=SenseVoiceService,
        model_id=MODEL_DIR,
        mode="batch",
    ),
    "paraformer-streaming": ASRSpec(
        name="paraformer-streaming",
        service_cls=StreamingParaformerService,
        model_id=STREAMING_MODEL_DIR,
        mode="stream",
    ),
}

_active_service = None
_active_model = ASR_MODEL if ASR_MODEL in _SPECS else "sensevoice"


def available_models() -> list[str]:
    """所有可用的引擎名"""
    return list(_SPECS)


def get_active_model_name() -> str:
    """当前激活的引擎名"""
    return _active_model


def get_model_dir(name: str) -> str:
    """指定引擎当前使用的模型路径/别名"""
    spec = _SPECS.get(name)
    return spec.model_id if spec else ""


def set_model_dir(name: str, model_dir: str) -> None:
    """更新引擎模型路径并重置已加载服务（不加载模型）"""
    global _active_service
    spec = _SPECS.get(name)
    if spec is None:
        raise ValueError(f"未知模型: {name!r}，可选值: {', '.join(_SPECS)}")
    if not model_dir:
        return
    _SPECS[name] = ASRSpec(spec.name, spec.service_cls, model_dir, spec.mode)
    if _active_service is not None and _active_service.name == name:
        _active_service = None


def set_punc_model_dir(model_dir: str) -> None:
    """更新流式标点模型路径（运行时生效）"""
    if model_dir:
        config.STREAMING_PUNC_MODEL_DIR = model_dir


def set_active_model(name: str) -> None:
    """切换当前引擎（只替换单例，模型保持懒加载）"""
    global _active_service, _active_model
    if name not in _SPECS:
        raise ValueError(
            f"未知的 ASR_MODEL: {name!r}，可选值: {', '.join(_SPECS)}"
        )
    _active_model = name
    _active_service = None


def get_asr_service():
    """返回当前 ASR_MODEL 对应的服务单例（不触发模型加载）"""
    global _active_service
    spec = _SPECS.get(_active_model)
    if spec is None:
        raise ValueError(
            f"未知的 ASR_MODEL: {_active_model!r}，可选值: {', '.join(_SPECS)}"
        )
    if _active_service is None or _active_service.name != spec.name:
        _active_service = spec.service_cls(spec)
    return _active_service
