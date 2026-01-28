# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作提供指导。

## 项目概述

多语音理解服务，支持流式 ASR（自动语音识别）。

## 技术栈

### 后端

- Python API: FastAPI 服务
- ASR 引擎: [SenseVoice (FunAudioLLM)](https://github.com/FunAudioLLM/SenseVoice/blob/main/README_zh.md) via [FunASR](https://github.com/modelscope/FunASR/blob/main/docs/tutorial/README_zh.md)
- 模型路径: `models/SenseVoiceSmall`

### 前端

- Web: React + TypeScript + Vite + TailwindCSS + shadcn/ui
- 桌面客户端: Electron + React + TypeScript

### 部署

- Docker: 容器化部署后端服务

## Python 环境

项目使用 uv 管理 Python 依赖。

### 设置代理（7897 端口）

Windows CMD:

```cmd
set http_proxy=http://localhost:7897
set https_proxy=http://localhost:7897
```

Windows PowerShell:

```powershell
$env:http_proxy="http://localhost:7897"
$env:https_proxy="http://localhost:7897"
```

Linux/macOS Zsh:

```zsh
export http_proxy=http://localhost:7897
export https_proxy=http://localhost:7897
```

### 使用 uv

```bash
# 进入 api 目录
cd api

# 初始化项目
uv init

# 同步依赖（自动使用 .venv）
uv sync

# 运行 demo 脚本（uv run 或直接 python 都可以）
uv run python demo/sensevoice_demo.py

# 启动 FastAPI 服务
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 添加依赖（在中国大陆需要先设置代理）
$env:http_proxy="http://localhost:7897"
$env:https_proxy="http://localhost:7897"
uv add <package-name>
```

## 项目结构

```
phonetics-2/
├── api/           # FastAPI 服务 + Demo 脚本（共享 uv venv）
│   ├── src/       # API 源码
│   ├── demo/      # Demo 脚本
│   └── pyproject.toml
├── web/           # React 前端
├── desktop/       # Electron 桌面客户端
└── docs/          # 文档
```

## 文档规范

- README: 项目说明和快速开始
- docs/: 设计文档、详细文档、使用指南
- 代码注释: 复杂逻辑需要注释
- markdown禁止使用加粗符号：*

## 版本与提交规范

### 语义化版本 (Semantic Versioning)

- 主版本号: 不兼容的 API 变更
- 次版本号: 向后兼容的功能新增
- 修订号: 向后兼容的问题修复

### 提交规范 (Conventional Commits)

```
<type>[scope]: <description>

[optional body]

[optional footer]
```

### 类型 (Type)

- feat: 新功能
- fix: 修复 bug
- docs: 文档更新
- style: 代码格式（不影响功能）
- refactor: 重构
- perf: 性能优化
- test: 测试
- chore: 构建或辅助工具更新

### 示例

```
feat(api): 添加流式 ASR 接口
fix(demo): 修复音频文件路径问题
docs: 更新 README
```

### CHANGELOG

使用 conventional-changelog 自动生成 CHANGELOG.md。

## 开发说明

- Demo 脚本放在 api/demo/ 目录下，共享同一个 uv 虚拟环境
- 桌面客户端使用 Electron，支持通过全局快捷键激活语音输入
- ASR 识别结果可通过 Electron API 直接注入到文本输入框
