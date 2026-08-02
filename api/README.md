# Phonetics-2 API

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

## ASR 模型切换

通过环境变量 `ASR_MODEL` 选择引擎（桌面端与 API 共用）：

- `sensevoice`（默认）：整段识别，沿用 `MODEL_DIR` 指定的模型
- `paraformer-streaming`：流式识别，模型名或本地路径由 `STREAMING_MODEL_DIR` 指定

流式模型与标点模型默认优先加载项目根目录 `models/` 下的本地副本
（`models/paraformer-zh-streaming`、`models/ct-punc`），目录不存在时
回退到 FunASR 在线别名（首次运行会自动下载到模型缓存）。环境变量里的
模型路径支持绝对路径或相对路径（相对路径统一按项目根目录解析）。

流式相关参数：

- `ASR_STREAM_CHUNK_MS`：chunk 粒度（默认 600ms，CPU 压力大时可调大到 960）
- `ASR_PUNC`：是否给最终文本补标点（默认 true，使用 ct-punc；
  仅用于 API 上传/批量识别路径，桌面持续听写不自动补标点）
- `STREAMING_PUNC_MODEL_DIR`：标点模型的模型名或本地路径

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

- F8: 开始/停止录音或监听（流式模式会实时往焦点窗口打字）
- Esc: 录音/监听中取消，并删除已打出的流式文本
- 退出: 托盘右键菜单选择"退出"

流式模式（`ASR_MODEL=paraformer-streaming`）是持续听写：按 F8 开始后，
说话内容以 600ms 粒度直接累积打进 F8 按下时的焦点窗口（之后切走焦点
也不影响，会自动拉回）；再按 F8 停止，只冲刷尾部剩余音频并追加最后一
段文字，不做删除、不做整段替换、不自动补标点。Esc 立即停止但不冲刷
尾部。注意流式打字依赖普通文本输入环境，vim、终端、密码框等特殊场景
可能不兼容。

### 系统托盘图标

客户端启动后在 Windows 右下角通知区域显示托盘图标，通过颜色变化反映当前状态：

| 状态 | 图标颜色 | 说明 |
|------|---------|------|
| 加载模型 | 🔵 蓝色 | 启动后自动进入 |
| 空闲中 | 🟢 绿色 | 等待 F8 触发录音 |
| 录音中 | 🔴 红色 | 正在录制麦克风音频 |
| 流式监听中 | 🔴 红色 | 正在监听并实时输出文本 |
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

- [x] 识别历史入库：SQLite 记录每次识别的文本、录音时长、推理耗时、RTF 与内存指标
- [x] 桌面客户端迁移到 api 目录，直接调用本地模型，去掉 HTTP 层，提升速度，监听输入设备事件
- [x] 第一个可用 bat 启动脚本，版本管理，合并到 master
- [x] FunASR 内存三倍占用：已查明根因（Windows 特性）
  - 详见 [docs/memory-experiment-report.md](docs/memory-experiment-report.md)
- [ ] 桌面端优化 `desktop/audio_recorder.py`
  - 日志优化
  - 快捷键自定义
  - macOS 适配
- [ ] 报表分析：每日/每月使用频率、延迟与 RTF 趋势、模型占比（基于历史数据）
- [x] 模型切换（环境变量版）：模型注册表 + `ASR_MODEL` 切换，SenseVoice 整段 / Paraformer 流式
- [x] 桌面端流式识别：paraformer-zh-streaming 边说边出字，F8 开关持续听写，
  不做整段替换
- [ ] 流式断句补标点：FSMN-VAD 检测停顿自动断句，逐句补标点，不影响连续听写
- [ ] 模型切换 UI（阶段三）：启动不加载模型，下拉/托盘选择模型后再加载
