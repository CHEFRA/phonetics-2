# 全局语音输入桌面客户端实现计划

## Context

用户需要实现一个全局语音输入工具：按下快捷键开始录音 → 再次按下结束录音 → ASR 识别 → 自动填充文本到任意焦点文本框（任何 App 的文本框）。

当前项目已有：
- FastAPI + SenseVoice ASR 服务（`localhost:8000`）
- Web 端录音 UI 组件

缺失：桌面客户端、全局快捷键、后台录音、文本填充到任意窗口

## 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                    Electron Main Process                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Shortcut   │  │   Tray     │  │   Voice    │            │
│  │  Manager    │  │  Manager   │  │  Manager   │            │
│  │ (globalShort│  │            │  │  录音→识别→│            │
│  │   cut)      │  │            │  │  填充流程  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                           │                                   │
│                    ┌──────┴──────┐                           │
│                    │ FFmpeg 录音  │  ← 后台录制，不依赖浏览器  │
│                    └─────────────┘                           │
└───────────────────────────┬──────────────────────────────────┘
                            │ IPC (contextBridge)
┌───────────────────────────┴──────────────────────────────────┐
│                    Renderer Process (React UI)                │
│  设置面板、状态显示、快捷键自定义                               │
└──────────────────────────────────────────────────────────────┘
```

## 实现步骤

### Step 1: 初始化 Electron 项目

创建 `desktop/` 目录和基础结构：

```
desktop/
├── src/
│   ├── main/
│   │   ├── index.ts          # 主进程入口
│   │   ├── shortcutManager.ts # 全局快捷键
│   │   ├── trayManager.ts     # 系统托盘
│   │   ├── voiceManager.ts    # 录音→ASR→填充 核心流程
│   │   └── services/
│   │       ├── audioRecorder.ts  # FFmpeg 录音
│   │       ├── asrClient.ts     # 调用 FastAPI
│   │       └── textInserter.ts  # 剪贴板+粘贴
│   ├── preload/
│   │   └── index.ts
│   └── renderer/
│       ├── App.tsx
│       └── Settings.tsx
├── package.json
└── tsconfig.json
```

### Step 2: 全局快捷键注册 (ShortcutManager)

使用 Electron `globalShortcut` API：

- 默认快捷键：`CommandOrControl+Shift+V`
- 注册成功/失败反馈给用户
- 支持用户自定义快捷键

```typescript
// src/main/shortcutManager.ts
globalShortcut.register('CommandOrControl+Shift+V', () => {
  voiceManager.toggleRecording();
});
```

### Step 3: 后台录音 (AudioRecorder)

使用 FFmpeg 作为录音后端（跨平台兼容性好）：

- **macOS**: `-f avfoundation -i :0`
- **Windows**: `-f dshow -i audio=...`
- **Linux**: `-f alsa -i default`
- 输出格式: 16kHz WAV (ASR 最佳)
- 临时文件: `/tmp/voice_input_<timestamp>.wav`

```typescript
// src/main/services/audioRecorder.ts
spawn('ffmpeg', ['-f', 'avfoundation', '-i', ':0',
                 '-ar', '16000', '-ac', '1',
                 '-c:a', 'pcm_s16le', outputPath]);
```

### Step 4: ASR 调用 (ASRClient)

调用已有 FastAPI 接口：

```typescript
// POST http://localhost:8000/api/v1/asr
// Response: { "text": "识别结果" }
```

### Step 5: 文本填充 (TextInserter)

使用剪贴板 + 模拟粘贴：

1. 保存原剪贴板内容
2. 写入识别文本到剪贴板
3. 模拟 `Ctrl+V` / `Cmd+V`
4. 延迟恢复原剪贴板内容

依赖: `robotjs` 或 `node-robot` 模拟键盘

### Step 6: 系统托盘 (TrayManager)

托盘菜单：
- 状态显示（就绪/录音中/识别中）
- 最近识别记录（点击复制）
- 设置入口
- 退出

### Step 7: React 设置界面

- 快捷键配置
- ASR 服务地址配置
- 录音设备选择
- 界面语言

## 关键文件

| 文件 | 作用 |
|------|------|
| `api/routers/asr.py` | 现有 ASR 接口，客户端对接点 |
| `web/src/components/AudioRecorder.tsx` | 参考现有录音 UI 逻辑 |

## 技术栈

- **Electron 28+** - 桌面框架
- **React 18** - UI
- **Zustand** - 状态管理
- **FFmpeg** - 录音（需打包或用户安装）
- **robotjs** - 模拟键盘输入
- **electron-builder** - 打包

## 验证方式

1. 启动 FastAPI 服务: `cd api && uv run uvicorn src.main:app`
2. 启动 Electron: `cd desktop && npm run dev`
3. 按 `Ctrl+Shift+V` 开始录音
4. 再次按 `Ctrl+Shift+V` 结束录音
5. 验证文本是否填充到任意文本框（如记事本、浏览器）
