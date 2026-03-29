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

## 运行 Demo 脚本

```bash
uv run python demo/sensevoice_demo.py
```

## 启动 API 服务

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 测试 ASR 接口

```bash
curl -X POST "http://localhost:8000/api/v1/asr" -F "file=@../data/audio/zh.mp3"
```
