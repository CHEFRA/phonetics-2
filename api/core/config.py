from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 模型路径
MODEL_DIR = (BASE_DIR / "models" / "SenseVoiceSmall").as_posix()

# 设备配置
DEVICE = "cpu"  # 有显卡可改为 "cuda"

# 模型配置
MODEL_KWARGS = {
    "disable_update": True,
}