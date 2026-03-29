import os
from pathlib import Path
from dotenv import load_dotenv
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

# 基于脚本所在目录定位项目根目录和 .env 文件
SCRIPT_DIR = Path(__file__).resolve().parent
API_DIR = SCRIPT_DIR.parent.parent  # api 目录
PROJECT_DIR = API_DIR.parent        # 项目根目录

# 加载 .env 文件
load_dotenv(API_DIR / ".env")

# 模型配置
model_dir = os.getenv("MODEL_DIR")
device = os.getenv("DEVICE", "cpu")

# 音频路径（相对于项目根目录）
audio_path = PROJECT_DIR / "data" / "audio" / "zh.mp3"

model = AutoModel(
    model=model_dir,
    device=device,
    disable_update=True,
)

res = model.generate(
    input=str(audio_path),  # FunASr.generate() 只接受字符串路径
    language="auto",
    use_itn=True,
)

text = rich_transcription_postprocess(res[0]["text"])
print(text)
