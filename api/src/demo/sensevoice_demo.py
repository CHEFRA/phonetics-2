import time
from pathlib import Path

import psutil
from dotenv import load_dotenv

from src.core.asr_registry import get_asr_service

# 基于脚本所在目录定位项目根目录和 .env 文件
SCRIPT_DIR = Path(__file__).resolve().parent
API_DIR = SCRIPT_DIR.parent.parent  # api 目录
PROJECT_DIR = API_DIR.parent  # 项目根目录

# 加载 .env 文件
load_dotenv(API_DIR / ".env")

# 音频路径（相对于项目根目录）
audio_path = PROJECT_DIR / "data" / "audio" / "zh.mp3"

proc = psutil.Process(os.getpid())
mem_before = proc.memory_info().rss
start_time = time.time()

asr_service = get_asr_service()
asr_service.get_model()

duration = time.time() - start_time
mem_after = proc.memory_info().rss
print(
    f"[{asr_service.name}] 模型加载完成 | "
    f"耗时={duration:.2f}s | "
    f"内存={mem_before / 1024 / 1024:.0f}MB→{mem_after / 1024 / 1024:.0f}MB | "
    f"增量={(mem_after - mem_before) / 1024 / 1024:+.0f}MB"
)

text = asr_service.recognize(str(audio_path))
print(text)
