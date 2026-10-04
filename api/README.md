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

### macOS（Apple Silicon）终端版

macOS 上为独立实现（`desktop/macos/`），线程模型与 Windows 不同
（菜单栏图标必须占用主线程），不改动 Windows 侧任何代码。

```bash
# 在 api 目录下启动
uv run python -m desktop.macos.mac_client

# 或双击启动脚本（Finder 中）
scripts/phonetics-asr-mac.command
```

首次使用需要在 系统设置 → 隐私与安全性 中，把运行本程序的终端 App
（如 Terminal / iTerm）授权给以下权限：

- 辅助功能：识别结果模拟 Cmd+V 粘贴
- 输入监控：全局热键监听
- 麦克风：录音（首次录音时系统弹窗，允许即可）

操作：

- F8: 开始/停止录音（Mac 键盘 F8 默认是媒体键，需同时按 fn，或在
  系统设置开启"将 F1、F2 等键用作标准功能键"）
- Esc: 录音中取消录音
- 退出: 菜单栏图标下拉菜单选择"退出"，或终端 Ctrl+C

菜单栏图标颜色含义与 Windows 托盘一致（蓝=加载、绿=空闲、红=录音、
黄=处理）。macOS 没有悬停提示，"状态 + 实时内存"显示在下拉菜单
第一项，识别结果通过系统通知弹出。

自定义热键: 支持 HOTKEY 环境变量,详见下方「快捷键自定义(HOTKEY)」。

## 快捷键自定义(HOTKEY)

macOS 终端版客户端通过 `api/.env` 的 `HOTKEY` 环境变量自定义全局热键:

```bash
HOTKEY=ctrl+option+cmd
```

修改后重启客户端生效,启动时终端会打印当前生效的热键。不配置时默认 `f8`。

### 语法

- 多个键用 `+` 连接,顺序无关、大小写不敏感: `ctrl+shift+space` 与 `Shift + CTRL + Space` 等价
- 触发方式: 同时按住全部按键(录音中按 Esc 仍可取消)
- Windows 桌面客户端暂不支持环境变量配置,固定为 F8;如需修改,编辑
  `desktop/asr_client.py` 中的 `HOTKEY_KEYS` 常量

### 可用按键

| 写法 | 对应键 | 说明 |
|------|--------|------|
| ctrl / control | ⌃ Control | |
| shift | ⇧ Shift | |
| alt / option | ⌥ Option | |
| cmd / command | ⌘ Command | |
| space | 空格 | |
| tab | Tab | |
| enter / return | 回车 | |
| f1 ~ f20 | 功能键 | Mac 键盘需按 fn,或开启"将 F1、F2 等键用作标准功能键" |
| 单个字符 | 字母、数字等 | 如 `a`、`1` |

不支持 `fn` 键: pynput 在 macOS 上未暴露该键码,程序收不到 fn 事件。

### 组合推荐与常见冲突

| 组合 | 冲突情况 | 结论 |
|------|----------|------|
| 三个修饰键(如 ctrl+option+cmd) | 无 | 推荐 |
| 修饰键 + space/tab(如 ctrl+shift+space) | 少见 | 推荐 |
| cmd+space | Spotlight | 不可用 |
| ctrl+space | 多数中文输入法的中英切换 | 不建议 |
| option+space | Raycast / Alfred 默认启动键 | 不建议 |
| cmd+tab、cmd+` | 切换应用,日常高频触发 | 不可用 |
| f5 | 听写 | 不建议 |
| f6 | 专注模式 | 不建议 |
| f7 ~ f12 | 媒体与音量键 | 需 fn,体验差 |
| 含 esc | 与"录音中取消"冲突 | 不建议 |
| option+字母 | 打特殊字符(如 ß、å)时误触 | 不建议 |

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
- [x] macOS 适配：终端版语音输入（Apple Silicon），菜单栏图标 + 全局热键，
  支持 HOTKEY 环境变量自定义热键，见上方 macOS 章节
- [ ] 桌面端优化 `desktop/audio_recorder.py`
  - 日志优化
  - 快捷键自定义（Windows 端；macOS 已支持 HOTKEY 环境变量）
- [ ] 报表分析：每日/每月使用频率、延迟与 RTF 趋势、模型占比（基于历史数据）
- [ ] 模型切换：模型注册表 + 下拉选择，SenseVoice 整段 / Paraformer 流式，设置持久化
- [ ] 流式识别：FSMN-VAD + paraformer-zh-streaming，边说边出字，松键定稿并自动粘贴，可选 SenseVoice 精修
