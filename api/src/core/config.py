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


def _resolve_model_path(value: str) -> str:
    """模型路径解析：绝对路径原样保留，相对路径按项目根目录解析，
    纯模型别名（如 paraformer-zh-streaming、ct-punc）原样传给 FunASR"""
    if not value:
        return value
    if os.path.isabs(value):
        return value
    # 含路径分隔符或点开头视为路径，否则视为 FunASR 模型别名
    if "/" in value or "\\" in value or value.startswith("."):
        return str((BASE_DIR / value).resolve())
    return value


# 流式模型（paraformer-streaming）的模型名或本地路径；
# 优先使用项目 models/ 下的本地副本，不存在时才回退到 FunASR 在线别名
_LOCAL_STREAMING_MODEL_DIR = BASE_DIR / "models" / "paraformer-zh-streaming"
STREAMING_MODEL_DIR = _resolve_model_path(
    os.getenv(
        "STREAMING_MODEL_DIR",
        str(_LOCAL_STREAMING_MODEL_DIR)
        if _LOCAL_STREAMING_MODEL_DIR.exists()
        else "paraformer-zh-streaming",
    )
)

# 流式标点模型（ct-punc）的模型名或本地路径
_LOCAL_PUNC_MODEL_DIR = BASE_DIR / "models" / "ct-punc"
STREAMING_PUNC_MODEL_DIR = _resolve_model_path(
    os.getenv(
        "STREAMING_PUNC_MODEL_DIR",
        str(_LOCAL_PUNC_MODEL_DIR) if _LOCAL_PUNC_MODEL_DIR.exists() else "ct-punc",
    )
)

# 流式识别 chunk 粒度（毫秒），默认 600ms；可调大如 960 以降低 CPU 压力
ASR_STREAM_CHUNK_MS = int(os.getenv("ASR_STREAM_CHUNK_MS", "600"))

# 流式最终文本是否补标点（ct-punc），默认开启
ASR_PUNC = os.getenv("ASR_PUNC", "true").lower() in ("1", "true", "yes", "on")

# 数据库文件路径（默认项目根目录 data/phonetics.db，可用环境变量覆盖；
# 相对路径统一按项目根目录解析，避免因启动目录不同产生多个数据库文件）
DB_PATH = Path(
    _resolve_model_path(
        os.getenv("DB_PATH", str(BASE_DIR / "data" / "phonetics.db"))
    )
)
