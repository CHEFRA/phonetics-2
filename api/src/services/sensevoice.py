import os
import re
import time

import psutil
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

from src.core.config import DEVICE, MODEL_KWARGS

# 常见 emoji 字符区间，用于清除识别结果中的表情符号
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"  # 表情、符号、旗帜
    "\U00002600-\U000027BF"  # 杂项符号、装饰符号（含 ❓）
    "\U00002300-\U000023FF"  # 杂项技术符号
    "\U00002B00-\U00002BFF"  # 杂项符号和箭头
    "\U0000FE00-\U0000FE0F"  # 变体选择符
    "\U0000200D"             # 零宽连接符
    "\U000020E3"             # 组合围音符
    "]"
)


def strip_emoji(text: str) -> str:
    """去掉文本中的 emoji

    SenseVoice 会把情绪标签（如 <|SAD|>）转成 emoji 并默认加在句尾，
    这里统一清除，避免识别结果粘贴进文档时带上表情符号。
    """
    return _EMOJI_RE.sub("", text).strip()


class SenseVoiceService:
    """SenseVoice 整段识别服务（非流式）"""

    def __init__(self, spec=None):
        """spec: asr_registry.ASRSpec，缺省时使用历史默认值"""
        self.name = spec.name if spec else "sensevoice"
        self.model_id = spec.model_id if spec else "SenseVoiceSmall"
        self.mode = spec.mode if spec else "batch"
        self._model = None

    def reset_stream(self):
        """SenseVoice 不支持流式，仅用于统一接口"""
        return None

    def get_model(self):
        if self._model is None:
            proc = psutil.Process(os.getpid())
            mem_before = proc.memory_info().rss
            start_time = time.time()

            self._model = AutoModel(
                model=self.model_id,
                device=DEVICE,
                **MODEL_KWARGS,
            )

            duration = time.time() - start_time
            mem_after = proc.memory_info().rss
            delta_mb = (mem_after - mem_before) / 1024 / 1024

            print(
                f"[sensevoice] 模型加载完成 | "
                f"耗时={duration:.2f}s | "
                f"内存={mem_before / 1024 / 1024:.0f}MB→{mem_after / 1024 / 1024:.0f}MB | "
                f"增量={delta_mb:+.0f}MB"
            )
        return self._model

    def recognize(self, audio_path: str, language: str = "auto", use_itn: bool = True):
        model = self.get_model()
        res = model.generate(
            input=audio_path,
            language=language,
            use_itn=use_itn,
        )
        text = rich_transcription_postprocess(res[0]["text"])
        text = strip_emoji(text)
        return text


# 全局服务实例
sensevoice_service = SenseVoiceService()
