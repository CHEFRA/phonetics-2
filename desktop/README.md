# 桌面客户端

全局热键语音输入客户端，按 `Ctrl+Shift+Space` 开始/停止录音，识别结果自动粘贴到焦点窗口。

## 系统依赖

需要安装以下系统库：

```bash
# Ubuntu/Debian
sudo apt install libportaudio2

# macOS
brew install portaudio
```

## 快速开始

```bash
cd desktop

# 安装 Python 依赖
uv sync

# 启动客户端
uv run python -m src.asr_client
```

## 使用方式

1. 运行客户端，终端显示 `监听中，按 Ctrl+Shift+Space 开始录音，按 Esc 退出`
2. 按 `Ctrl+Shift+Space` 开始录音，终端显示 `🔴 录音中...`
3. 再次按 `Ctrl+Shift+Space` 停止录音，终端显示 `⏹ 停止录音，识别中...`
4. 识别结果自动粘贴到当前焦点窗口，并打印 `✅ {识别结果}`
5. 按 `Esc` 退出客户端

## 注意事项

- 客户端需要 ASR API 服务运行在 `http://localhost:8000`
- Linux 桌面环境下需要 `libportaudio2` 系统库
- 全局热键在 WSL 环境下不可用，请在真实 Linux 桌面环境使用
