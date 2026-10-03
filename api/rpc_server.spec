# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包桌面 RPC 子进程

使用 onedir 模式（torch 体积大，onefile 启动解压太慢）。
console=True 保留 stdin/stdout 供 Electron 走 stdio RPC，
Electron 侧用 windowsHide 隐藏控制台窗口。
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

for package in ("funasr", "modelscope", "torch", "torchaudio"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += collect_submodules("pynput")
hiddenimports += collect_submodules("sounddevice")
hiddenimports += collect_submodules("soundfile")
hiddenimports += collect_submodules("pyperclip")
hiddenimports += [
    "asr_client",
    "rpc_protocol",
    "hotkey",
    "audio_recorder",
    "stream_typer",
    "tray_icon",
]

a = Analysis(
    ["desktop/rpc_server.py"],
    pathex=[".", "desktop"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="phonetics-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="phonetics-sidecar",
)
