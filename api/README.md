# Phonetics-2 API

## TODO

- [ ] api\desktop\audio_recorder.py
  - [ ] 日志优化
  - [ ] 快捷键自定义
  - [ ] macos适配
- [ ] funasr内存三倍占用优化
- [x] 第一个可用bat，版本管理，合并到master
- [x] 将桌面客户端脚本迁移到 api 目录下，直接调用本地模型，去掉 HTTP 层，提升速度。监听输入设备事件。
- [x] SQLite 识别历史入库（文本、录音时长、推理耗时、RTF）

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
# 安装所有依赖（含命令行客户端 + 系统托盘）
uv sync --all-extras

# 或按需选择：
# uv sync --extra cli              # 仅命令行客户端（无托盘图标）
# uv sync --extra cli --extra tray # 命令行客户端 + 系统托盘

uv run python desktop/asr_client.py
```

> 系统托盘为可选功能（依赖 `pystray` + `Pillow`），未安装时客户端正常运行，只是没有托盘图标。

操作：

- F8: 开始/停止录音
- Esc: 录音中取消录音
- 退出: 托盘右键菜单选择"退出"

### 系统托盘图标

客户端启动后在 Windows 右下角通知区域显示托盘图标，通过颜色变化反映当前状态：

| 状态 | 图标颜色 | 说明 |
|------|---------|------|
| 加载模型 | 🔵 蓝色 | 启动后自动进入 |
| 空闲中 | 🟢 绿色 | 等待 F8 触发录音 |
| 录音中 | 🔴 红色 | 正在录制麦克风音频 |
| 处理中 | 🟡 黄色 | 正在识别音频 |

右键菜单可查看当前状态或退出程序。识别完成后右下角弹出气泡通知显示识别文字。

鼠标悬停托盘图标可查看当前状态与实时内存占用（每 2 秒刷新，口径与任务管理器一致）。

### 启动脚本

`scripts/phonetics-asr.bat` 是一键启动脚本，两种使用方式：

- 直接双击：打开 `api/scripts/` 文件夹，双击 `phonetics-asr.bat`
- 桌面快捷方式（方便日常使用）：
  1. 打开 `api/scripts/` 文件夹
2. 右键 `phonetics-asr.bat` → 发送到 → 桌面快捷方式
3. 创建后双击桌面图标启动

## 识别历史记录

桌面客户端和 API 服务每次识别都会写入本地 SQLite 数据库（默认项目根目录
`data/phonetics.db`，可用环境变量 `DB_PATH` 覆盖），自动创建，无需手工初始化。

每条记录包含：

- 识别文本、模型、模式（整段/流式）、语言
- 录音时长、推理耗时、RTF（推理耗时/录音时长）
- 推理前后进程内存
- 状态（success / empty / error）

识别结果会自动清除 emoji 表情符号。

命令行快速查看统计：

```bash
cd api
uv run python -m src.services.history
```

数据库表结构与字段说明见 [docs/database.md](docs/database.md)。

## 路线图

后续三个规划需求：

- [x] 识别历史入库：SQLite 记录每次识别的文本、录音时长、推理耗时、RTF 与内存指标
- [ ] 报表分析：每日/每月使用频率、延迟与 RTF 趋势、模型占比（基于历史数据）
- [ ] 模型切换：模型注册表 + 下拉选择，SenseVoice 整段 / Paraformer 流式，设置持久化
- [ ] 流式识别：FSMN-VAD + paraformer-zh-streaming，边说边出字，松键定稿并自动粘贴，可选 SenseVoice 精修
