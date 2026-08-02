"""ASR 引擎注册表

通过环境变量 ASR_MODEL 选择当前使用的引擎：
  - sensevoice: SenseVoice 整段识别（默认，行为与历史版本一致）
  - paraformer-streaming: FunASR 流式 Paraformer

统一入口 get_asr_service() 返回当前引擎的服务单例，
桌面端、API、demo 都从这里取服务，不再直接 import 具体服务。
后续阶段三（启动不加载模型、UI 选择模型）可在此注册表基础上扩展，
例如把配置来源从环境变量换成数据库 settings 表。
"""

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


def available_models() -> list[str]:
    """所有可用的引擎名"""
    return list(_SPECS)


def get_asr_service():
    """返回当前 ASR_MODEL 对应的服务单例（不触发模型加载）"""
    global _active_service
    spec = _SPECS.get(ASR_MODEL)
    if spec is None:
        raise ValueError(
            f"未知的 ASR_MODEL: {ASR_MODEL!r}，可选值: {', '.join(_SPECS)}"
        )
    if _active_service is None or _active_service.name != spec.name:
        _active_service = spec.service_cls(spec)
    return _active_service
