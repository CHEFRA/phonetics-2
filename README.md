# Phonetics-2

多语音理解服务，支持流式 ASR（自动语音识别）。

## 技术栈

- **ASR 引擎**: [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) via FunASR
- **后端**: FastAPI + Python
- **前端**: React + TypeScript + Vite + TailwindCSS
- **桌面客户端**: Python (pynput 全局热键 + FunASR)

## 模块导航

| 模块 | 说明 | 文档 |
|------|------|------|
| api/ | FastAPI 后端服务、Demo 脚本、桌面客户端 | [README](api/README.md) |
| web/ | React 前端 | (开发中) |
| data/ | 测试音频数据 | - |
| docs/ | 设计文档 | - |
