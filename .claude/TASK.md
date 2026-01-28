# phonetics-2 项目计划

## 项目介绍

详见 [CLAUDE.md](../CLAUDE.md)

## 任务清单

### Step 1: Python Demo 脚本

- [x] 初始化 uv 项目 (`cd api && uv init`)
- [x] 下载模型到 models/SenseVoiceSmall 目录

```bash
git clone https://www.modelscope.cn/iic/SenseVoiceSmall.git models/SenseVoiceSmall
```

- [ ] 安装依赖

```bash
cd api
uv add funasr
uv sync
```

- [ ] 创建 demo/sensevoice_demo.py

参考: [SenseVoice 使用 funasr 部署](https://github.com/FunAudioLLM/SenseVoice/blob/main/README_zh.md#使用-funasr-部署)

### Step 2: FastAPI 服务

- [ ] 创建 src/main.py (FastAPI 应用)
- [ ] 创建 src/models.py (Pydantic 模型)
- [ ] 实现音频上传接口
- [ ] 实现流式 ASR 接口 (SSE)
- [ ] 添加 CORS 配置
- [ ] 创建 api/Dockerfile

### Step 3: React 前端

- [ ] 初始化 Vite + React + TypeScript 项目
- [ ] 安装 TailwindCSS + shadcn/ui
- [ ] 创建 AudioRecorder 组件
- [ ] 创建 StreamingASR 组件
- [ ] 实现 SSE 流式接收
- [ ] 对接后端 API

### Step 4: Electron 桌面客户端

- [ ] 初始化 Electron + React 项目
- [ ] 实现全局快捷键监听
- [ ] 实现录音功能
- [ ] 实现 API 调用
- [ ] 实现文本注入到光标位置
- [ ] 打包配置

## 快速开始

```bash
# 初始化
cd api
uv init
uv add fastapi uvicorn funasr python-multipart pydantic
uv sync

# 运行 Demo
uv run python demo/sensevoice_demo.py

# 启动 API 服务
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
