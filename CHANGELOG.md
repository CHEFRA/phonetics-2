# Changelog

本文件记录项目的所有重要变更，格式遵循 Conventional Commits。

## 0.8.0 (2026-10-04)

### Features

- macos-tray: 终端版语音输入支持 macOS (Apple Silicon)，与 Windows 功能对齐（全局热键、录音、SenseVoice 本地识别、自动粘贴、菜单栏图标、识别历史入库）
- macos-tray: 支持 HOTKEY 环境变量自定义全局热键，默认 f8
- scripts: 添加 macOS 启动脚本 phonetics-asr-mac.command

### Bug Fixes

- macos-tray: pynput 键盘输入源查询与 NSApp 启动并发导致崩溃，改为进入托盘循环前启动热键监听
- macos-tray: Ctrl+C 经 NSApp.terminate 硬退出不落库，通过 applicationShouldTerminate 委托兜底清理
- macos-tray: 非打包进程默认 Prohibited 策略导致菜单栏图标不可见，声明 Accessory 激活策略修复

## 0.7.0 (2026-08-02)

### Features

- api: 识别历史入库并修复桌面端闪退
- desktop: 托盘悬浮提示显示实时内存占用
- desktop: 录音中按 Esc 取消录音，不退出程序

## 0.6.0 (2026-07-27)

### Features

- cli-tray: 添加系统托盘图标，重命名依赖组名称
- desktop: 将全局快捷键从 Ctrl+Shift+Space 改为 F8
- scripts: 添加windows桌面客户端启动bat脚本和README使用说明
- asr_client: 添加资源清理功能并处理键盘中断

### Bug Fixes

- desktop: 将模型推理移出 listener 线程，修复停止失效和粘贴异常

### Performance Improvements

- 模型加载: 添加内存和耗时监控

## 0.5.0 (2026-05-01)

### Features

- desktop: 桌面客户端迁移到 api/desktop，直接调用本地模型
- api: 添加 Windows 启动脚本以便于服务启动
- api: 在收到请求时添加时间戳信息
- api: 在发送 API 请求时添加时间戳信息

### Bug Fixes

- asr: 修复临时文件处理问题并支持原始文件后缀

## 0.4.0 (2026-04-06)

### Features

- api: 添加日志记录功能，记录ASR模型加载、请求处理和录音时长
- api: 重构 API 结构，添加 src 目录并更新相关路径
- 添加退出功能和录音触发锁，优化按键监听逻辑
- api: 添加 Windows 启动脚本

### Bug Fixes

- desktop: 修复粘贴功能 bug

## 0.3.0 (2026-03-29)

### Features

- 实现全局语音输入桌面客户端基础功能（待验证，wsl无法验证）
- api: 优化 API 服务和配置

## 0.2.0 (2026-03-22)

### Features

- api: 实现 FastAPI 服务和 ASR 接口

### Bug Fixes

- demo: 修复模型初始化并统一路径处理风格

## 0.1.0 (2026-01-29)

初始化项目结构，添加 SenseVoice Demo 脚本。
