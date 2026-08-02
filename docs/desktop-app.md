# 桌面应用（Electron + Python 子进程）

## 架构

桌面应用由两层组成：

- Electron 壳（web/）：负责窗口、系统托盘、安装包与生命周期管理；
  React 渲染进程只通过 preload 暴露的 window.desktop 桥收发消息。
- Python 子进程（api/desktop/rpc_server.py）：继续独占麦克风、全局热键
  （pynput）、FunASR 模型推理与 SQLite 写入；启动时不加载模型。

Electron 主进程通过 child_process 启动 Python 子进程，标准输入输出传输
JSON lines 协议；退出时先发 quit 再强制结束，避免留下孤儿进程。

```
React 渲染进程
  |  window.desktop.rpc / onEvent（contextBridge，contextIsolation）
Electron 主进程（窗口 + 托盘 + 子进程管理）
  |  stdio JSON lines
Python 子进程（热键、录音、FunASR、SQLite、模型下载）
```

桌面应用不经过 FastAPI 的 HTTP 层，保持既有「直接调用本地模型」的决策。

## RPC 协议

每行一个 JSON 对象。请求与响应通过 id 配对：

```json
{"id": 1, "method": "get_status", "params": {}}
{"id": 1, "ok": true, "result": {...}}
{"id": 1, "ok": false, "error": {"code": "RPC_ERROR", "message": "..."}}
```

事件为主动推送：

```json
{"event": "state", "data": {"state": "recording"}}
```

### 命令

| method | params | 说明 |
|--------|--------|------|
| get_status | - | 状态、当前模型、热键、内存、版本、路径 |
| toggle_record | - | 开始/停止录音（等价于热键） |
| cancel_record | - | 取消本次录音 |
| set_hotkey | hotkey | 设置并持久化全局热键（如 ctrl+shift+f8） |
| set_model | model | 切换引擎（sensevoice / paraformer-streaming） |
| set_settings | values | 批量保存设置并触发运行时副作用 |
| get_settings | - | 全部设置 + db_path / models_root |
| get_history | limit/offset/query/status/model | 分页历史 |
| get_stats | - | 概览、每日/每月、模型占比、延迟趋势 |
| get_models | - | 三个模型的状态与路径 |
| download_model | model | 异步下载（进度走事件） |
| quit | - | 结束会话并退出 |

### 事件

| event | data | 说明 |
|-------|------|------|
| ready | status | RPC 模式启动完成 |
| state | state | idle/recording/streaming/processing |
| recording_started | mode | 开始录音或监听 |
| partial | text | 流式实时文本 |
| result | 识别详情 | 一次识别完成（含 RTF、耗时） |
| recording_cancelled | - | 录音被取消 |
| model_changed | model/mode | 引擎切换 |
| hotkey_changed | hotkey | 热键变更 |
| settings_changed | 设置项 | 运行时设置生效 |
| download_started / download_progress / download_finished / download_error | model 等 | 模型下载进度 |

## 开发运行

前置条件：api 依赖已同步（uv sync --all-extras），模型放在 models/ 或通过
MODELS_ROOT / MODEL_DIR 环境变量指定。

```bash
cd web
npm install
npm run dev
```

dev.mjs 会同时启动 Vite 与 Electron；Python 子进程默认使用
api/.venv 的 python，可通过 PHONETICS_PYTHON 环境变量覆盖
（例如指向已有 venv 的解释器）。

## 打包（Windows）

```powershell
.\scripts\build-windows.ps1
```

依次执行：uv sync → PyInstaller 打包 Python 子进程（onedir，
api/dist/phonetics-sidecar）→ npm install → vite build →
electron-builder 出 NSIS 安装包（web/release/）。

安装包不包含模型：首次启动在「模型」页从 ModelScope 下载到用户数据目录
（Windows 为 %APPDATA%/Phonetics/models），也可把已有模型目录放到该位置。
数据库位于 %APPDATA%/Phonetics/phonetics.db。

PyInstaller 打包说明：rpc_server.spec 使用 collect_all 收集
funasr/modelscope/torch/torchaudio，console=True 保留 stdio
（Electron 以 windowsHide 启动，不显示控制台窗口）。

## macOS 备注

- 同一套代码可在 macOS 上构建：PyInstaller 出 sidecar，
  npm run dist:mac 出 DMG；必须在 macOS 环境执行。
- 首次运行需在「系统设置 - 隐私与安全性」授予辅助功能（全局热键）与
  麦克风权限。

## 冒烟测试

Electron 主进程支持 SMOKE_TEST=1：启动后等待子进程 ready，调用
get_status 后自动退出（0 成功 / 1 失败），供 CI 或无人值守验证。
