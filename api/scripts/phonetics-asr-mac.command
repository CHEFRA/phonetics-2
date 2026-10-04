#!/bin/zsh
# macOS 终端版语音输入客户端一键启动(全局热键 + 菜单栏图标)
# 双击本文件(Finder 中)即可在 Terminal 中启动
cd "$(dirname "$0")/.." || exit 1
.venv/bin/python -m desktop.macos.mac_client
if [ $? -ne 0 ]; then
    echo
    echo "[phonetics-asr] 程序异常退出,详见上方输出与日志: \$TMPDIR/phonetics-asr-mac.log"
    read "reply?按回车关闭窗口..."
fi
