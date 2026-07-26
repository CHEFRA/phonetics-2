# Phonetics-2 API

## TODO

- [ ] api\desktop\audio_recorder.py
  - [ ] 日志优化
  - [ ] 快捷键自定义
  - [ ] macos适配
- [ ] funasr内存三倍占用优化
- [ ] 第一个可用bat，版本管理，合并到master
- [x] 将桌面客户端脚本迁移到 api 目录下，直接调用本地模型，去掉 HTTP 层，提升速度。监听输入设备事件。

## 系统依赖

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Windows: 从 https://ffmpeg.org/download.html 下载并添加到 PATH
```

## 安装 Python 依赖

```bash
cd api
uv sync
```

## 配置

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

以下操作需要在api目录执行

## 下载模型

模型需要下载到项目根目录下的 `models/` 目录（与 `api/` 平级）。请确保已正确安装 git lfs。

```bash
# 回到项目根目录
cd ..

# 安装 git lfs（如已安装可跳过）
git lfs install

# 克隆模型到 models/SenseVoiceSmall
git clone https://www.modelscope.cn/iic/SenseVoiceSmall.git models/SenseVoiceSmall

# 完成后回到 api 目录
cd api
```

模型路径为 `models/SenseVoiceSmall`，项目默认从该路径加载模型。

参考：[SenseVoiceSmall - ModelScope](https://www.modelscope.cn/models/iic/SenseVoiceSmall)

## 运行 Demo 脚本

```bash
uv run python src/demo/sensevoice_demo.py
```

## 启动 API 服务

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Windows 双击启动

#### 服务在wsl

在 Windows 文件资源管理器中双击 `api/start.bat` 即可启动后台服务，窗口会保持打开以查看运行日志。

#### 服务在windows

`api\start-windows.bat`

## 测试 ASR 接口

```bash
curl -X POST "http://localhost:8000/api/v1/asr" -F "file=@../data/audio/zh.mp3"
```

## 桌面客户端（直接调用本地模型）

无需启动 API 服务，直接录制麦克风音频并识别。

```bash
uv sync --extra desktop
uv run python desktop/asr_client.py
```

操作：

- **F8**: 开始/停止录音
- **Esc**: 退出程序

### 启动脚本

`scripts/phonetics-asr.bat` 是一键启动脚本，两种使用方式：

- **直接双击**：打开 `api/scripts/` 文件夹，双击 `phonetics-asr.bat`
- **桌面快捷方式**（方便日常使用）：
  1. 打开 `api/scripts/` 文件夹
  2. 右键 `phonetics-asr.bat` → 发送到 → 桌面快捷方式
  3. 创建后双击桌面图标启动
