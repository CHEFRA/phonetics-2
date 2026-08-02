# Phonetics-2

多语音理解服务，支持流式 ASR（自动语音识别）。

## 技术栈

- ASR 引擎: [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) via FunASR
- 后端: FastAPI + Python
- 前端: React + TypeScript + Vite + TailwindCSS（开发中）
- 桌面客户端: Python (pynput 全局热键 + FunASR, 系统托盘)
- 本地数据库: SQLite（识别历史、使用频率与速度分析）

## 模块导航

| 模块 | 说明 | 文档 |
|------|------|------|
| api/ | FastAPI 后端服务、Demo 脚本、桌面客户端 | [README](api/README.md) |
| web/ | Electron 桌面应用（窗口 + 托盘 + 安装包） | [desktop-app.md](docs/desktop-app.md) |
| data/ | 测试音频数据 | - |
| api/docs/ | 设计文档与数据库字段说明 | - |

## 桌面应用

Electron + React 窗口控制台：状态概览、识别历史、统计报表、模型管理与
设置；Python 子进程继续负责全局热键、录音与本地模型推理。
架构与打包说明见 [docs/desktop-app.md](docs/desktop-app.md)。
