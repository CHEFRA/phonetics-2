from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

from src.core.config import MODEL_DIR, DEVICE, MODEL_KWARGS


class SenseVoiceService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls._model = AutoModel(
                model=MODEL_DIR,
                device=DEVICE,
                **MODEL_KWARGS,
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