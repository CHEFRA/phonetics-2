from pathlib import Path
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

# 使用 resolve() 获得绝对路径，防止相对路径在不同环境下失效
BASE_DIR = Path(__file__).resolve().parent
model_dir = (BASE_DIR.parent.parent / "models" / "SenseVoiceSmall").as_posix()

model = AutoModel(
    model=model_dir,
    device="cpu", # 如果有显卡，记得后续改成 "cuda"
)

# 处理音频路径（向上两级到项目根目录）
audio_path = BASE_DIR.parent.parent / "data" / "audio" / "zh.mp3"

res = model.generate(
    input=audio_path.as_posix(), # 关键点：统一使用 posix 风格字符串
    # cache={},
    language="auto",
    use_itn=True,
    # batch_size_s=60,
    # merge_vad=True,
    # merge_length_s=15,
)

text = rich_transcription_postprocess(res[0]["text"])
print(text)