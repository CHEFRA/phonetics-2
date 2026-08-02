import os
from pathlib import Path
from dotenv import load_dotenv

# 基于脚本所在目录定位项目根目录和 .env 文件
SCRIPT_DIR = Path(__file__).resolve().parent
API_DIR = SCRIPT_DIR.parent.parent  # api 目录
PROJECT_DIR = API_DIR.parent        # 项目根目录

# 加载 .env 文件
load_dotenv(API_DIR / ".env")

# 项目根目录
BASE_DIR = PROJECT_DIR

# 模型路径（从环境变量读取）
MODEL_DIR = os.getenv("MODEL_DIR", "/home/lcl/data/models/SenseVoiceSmall")

# 设备配置
DEVICE = os.getenv("DEVICE", "cpu")

# 模型配置
MODEL_KWARGS = {
    "disable_update": True,
}

# 当前使用的 ASR 引擎: sensevoice（整段识别） | paraformer-streaming（流式）
ASR_MODEL = os.getenv("ASR_MODEL", "sensevoice")

# 流式模型（paraformer-streaming）的模型名或本地路径；
# 优先使用项目 models/ 下的本地副本，不存在时才回退到 FunASR 在线别名
_LOCAL_STREAMING_MODEL_DIR = BASE_DIR / "models" / "paraformer-zh-streaming"
STREAMING_MODEL_DIR = os.getenv(
    "STREAMING_MODEL_DIR",
    str(_LOCAL_STREAMING_MODEL_DIR)
    if _LOCAL_STREAMING_MODEL_DIR.exists()
    else "paraformer-zh-streaming",
)

# 流式标点模型（ct-punc）的模型名或本地路径
_LOCAL_PUNC_MODEL_DIR = BASE_DIR / "models" / "ct-punc"
STREAMING_PUNC_MODEL_DIR = os.getenv(
    "STREAMING_PUNC_MODEL_DIR",
    str(_LOCAL_PUNC_MODEL_DIR) if _LOCAL_PUNC_MODEL_DIR.exists() else "ct-punc",
)

# 流式识别 chunk 粒度（毫秒），默认 600ms；可调大如 960 以降低 CPU 压力
ASR_STREAM_CHUNK_MS = int(os.getenv("ASR_STREAM_CHUNK_MS", "600"))

# 流式最终文本是否补标点（ct-punc），默认开启
ASR_PUNC = os.getenv("ASR_PUNC", "true").lower() in ("1", "true", "yes", "on")

# 数据库文件路径（默认项目根目录 data/phonetics.db，可用环境变量覆盖）
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "phonetics.db")))
