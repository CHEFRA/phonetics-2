import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 模型路径（从环境变量读取）
MODEL_DIR = os.getenv("MODEL_DIR", "/home/lcl/data/models/SenseVoiceSmall")

# 设备配置
DEVICE = os.getenv("DEVICE", "cpu")

# 模型配置
MODEL_KWARGS = {
    "disable_update": True,
}
