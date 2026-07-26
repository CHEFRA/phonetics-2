## 快捷键配置

支持通过配置文件或环境变量自定义快捷键。

### 配置文件

在项目目录创建 `config.json`：

```json
{
  "hotkey": "f8",
  "exit_key": "esc",
  "api_url": "http://localhost:8000/api/v1/asr"
}
```

支持的快捷键格式：

- `f8` - F8
- `ctrl+alt+v` - Ctrl+Alt+V
- `cmd+shift+s` - Command+Shift+S（macOS）

### 环境变量

```bash
export ASR_HOTKEY="f8"
export ASR_API_URL="http://localhost:8000/api/v1/asr"
```

### 优先级

环境变量 > 配置文件 > 默认值

### 默认快捷键

- Windows/Linux: `F8` 开始/停止录音，`Esc` 退出
- macOS: `Cmd+Shift+Space` 开始/停止录音，`Esc` 退出

---

## 日志功能

记录客户端运行状态到日志文件。

### 日志级别

- `DEBUG` - 调试信息
- `INFO` - 运行信息
- `WARNING` - 警告
- `ERROR` - 错误

### 日志格式

```
[2026-03-29 10:30:15] [INFO] 客户端已启动
[2026-03-29 10:30:20] [INFO] 开始录音
[2026-03-29 10:30:25] [INFO] 停止录音，识别中...
[2026-03-29 10:30:26] [INFO] 识别成功: 你好世界
[2026-03-29 10:30:26] [INFO] 已粘贴到焦点窗口
[2026-03-29 10:30:30] [ERROR] API 请求失败: Connection refused
```

### 日志配置（config.json）

```json
{
  "log_level": "INFO",
  "log_file": "asr_client.log",
  "log_max_size": "10MB",
  "log_backup_count": 3
}
```

### 日志存储

- Windows: `%APPDATA%/phonetics-2/asr_client.log`
- macOS: `~/Library/Logs/phonetics-2/asr_client.log`
- Linux: `~/.local/share/phonetics-2/asr_client.log`

---

## 可执行文件和 UI 界面

使用 Electron + React 构建独立桌面应用。

### UI 功能

1. **主界面**

   - 显示当前状态（监听中/录音中/识别中）
   - 显示快捷键说明
   - 显示识别历史（最近 10 条）
2. **设置界面**

   - 修改快捷键
   - 修改 API 地址
   - 日志级别配置
   - 开机自启动
3. **系统托盘**

   - 常驻托盘
   - 右键菜单：显示/隐藏窗口、退出

### 构建目标

- Windows: `phonetics-2-setup.exe`（NSIS 安装包）
- macOS: `phonetics-2.dmg`
- Linux: `phonetics-2.AppImage`

### 技术栈

```
Electron     # 桌面应用框架
React       # UI 框架
TypeScript  # 类型安全
Vite        # 构建工具
TailwindCSS # 样式
shadcn/ui   # UI 组件库
```
