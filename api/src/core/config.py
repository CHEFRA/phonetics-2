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


def _anchor_api_path(value: str) -> Path:
    """相对路径锚定到 api/ 目录，避免随启动目录（cwd）漂移"""
    path = Path(value)
    return path if path.is_absolute() else (API_DIR / path).resolve()


# 模型根目录（打包后由 Electron 指向用户数据目录；默认项目 models/）
MODELS_ROOT = _anchor_api_path(os.getenv("MODELS_ROOT") or str(BASE_DIR / "models"))


def _resolve_model_dir(env_key: str, local_name: str, fallback_alias: str) -> str:
    """优先环境变量，其次 MODELS_ROOT 下的本地副本，最后回退在线别名"""
    env_value = os.getenv(env_key)
    if env_value:
        return env_value
    local = MODELS_ROOT / local_name
    return str(local) if local.exists() else fallback_alias


# 模型路径（默认优先项目 models/ 下的本地副本，不存在时回退在线别名）
MODEL_DIR = _resolve_model_dir("MODEL_DIR", "SenseVoiceSmall", "SenseVoiceSmall")

# 设备配置
DEVICE = os.getenv("DEVICE", "cpu")

# 模型配置
MODEL_KWARGS = {
    "disable_update": True,
}

# 当前使用的 ASR 引擎: sensevoice（整段识别） | paraformer-streaming（流式）
ASR_MODEL = os.getenv("ASR_MODEL", "sensevoice")

# 流式模型（paraformer-streaming）的模型名或本地路径
STREAMING_MODEL_DIR = _resolve_model_dir(
    "STREAMING_MODEL_DIR", "paraformer-zh-streaming", "paraformer-zh-streaming"
)

# 流式标点模型（ct-punc）的模型名或本地路径
STREAMING_PUNC_MODEL_DIR = _resolve_model_dir(
    "STREAMING_PUNC_MODEL_DIR", "ct-punc", "ct-punc"
)

# 流式识别 chunk 粒度（毫秒），默认 600ms；可调大如 960 以降低 CPU 压力
ASR_STREAM_CHUNK_MS = int(os.getenv("ASR_STREAM_CHUNK_MS", "600"))

# 流式最终文本是否补标点（ct-punc），默认开启
ASR_PUNC = os.getenv("ASR_PUNC", "true").lower() in ("1", "true", "yes", "on")

# 数据库文件路径（默认项目根目录 data/phonetics.db，可用环境变量覆盖）
DB_PATH = _anchor_api_path(os.getenv("DB_PATH") or str(BASE_DIR / "data" / "phonetics.db"))
