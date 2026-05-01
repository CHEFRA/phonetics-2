import os
import time

import psutil
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

from src.core.config import MODEL_DIR, DEVICE, MODEL_KWARGS


class SenseVoiceService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            proc = psutil.Process(os.getpid())
            mem_before = proc.memory_info().rss
            start_time = time.time()

            cls._model = AutoModel(
                model=MODEL_DIR,
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
        return cls._model

    def recognize(self, audio_path: str, language: str = "auto", use_itn: bool = True):
        model = self.get_model()
        res = model.generate(
            input=audio_path,
            language=language,
            use_itn=use_itn,
        )
        text = rich_transcription_postprocess(res[0]["text"])
        return text


# 全局服务实例
sensevoice_service = SenseVoiceService()