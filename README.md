# Phonetics-2

多语音理解服务，支持流式 ASR（自动语音识别）。

## 技术栈

- **ASR 引擎**: [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) via FunASR
- **后端**: FastAPI + Python
- **前端**: React + TypeScript + Vite + TailwindCSS
- **桌面客户端**: Electron

## 项目结构

```
phonetics-2/
├── api/           # FastAPI 服务 + Demo 脚本
│   ├── demo/      # Demo 脚本
│   ├── src/       # API 源码
│   └── README.md  # API 文档
├── web/           # React 前端
├── desktop/       # Electron 桌面客户端
├── data/          # 测试音频数据
└── docs/          # 文档
```

## 快速开始

### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt install ffmpeg
```

### 2. 下载模型

```bash
git clone https://www.modelscope.cn/iic/SenseVoiceSmall.git models/SenseVoiceSmall
```

### 3. 启动 API 服务

```bash
cd api
uv sync
cp .env.example .env  # 根据需要修改配置
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 测试 ASR 接口

```bash
curl -X POST "http://localhost:8000/api/v1/asr" -F "file=@../data/audio/zh.mp3"
```

## API 文档

详见 [api/README.md](api/README.md)

## 开发说明

- API 使用 uv 管理依赖
- 模型路径通过 `api/.env` 配置
- 音频文件上传后使用 tempfile 自动清理
