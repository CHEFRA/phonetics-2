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
