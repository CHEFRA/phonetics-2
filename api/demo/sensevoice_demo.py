import os
from pathlib import Path
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

# 模型配置
model_dir = os.getenv("MODEL_DIR", "/home/lcl/data/models/SenseVoiceSmall")
device = os.getenv("DEVICE", "cpu")

model = AutoModel(
    model=model_dir,
    device=device,
    disable_update=True,
)

# 处理音频路径（向上两级到项目根目录）
BASE_DIR = Path(__file__).resolve().parent
audio_path = BASE_DIR.parent.parent / "data" / "audio" / "zh.mp3"

res = model.generate(
    input=audio_path.as_posix(),
    language="auto",
    use_itn=True,
)

text = rich_transcription_postprocess(res[0]["text"])
print(text)
