"""桌面客户端 stdio RPC 入口（供 Electron 子进程调用）

启动方式（开发）:
  uv run python desktop/rpc_server.py

协议与命令见 rpc_protocol.py 与 docs/desktop-app.md。
"""

import os
import sys
import threading

# 保证从 api 根目录 import src.*（独立运行/PyInstaller 场景）
_API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

from asr_client import ASRClient  # noqa: E402
from rpc_protocol import RPCServer  # noqa: E402


def main():
    client = ASRClient(use_tray=False, rpc_mode=True)
    server = RPCServer(client)
    client._event_sink = server.send_event
    server_thread = threading.Thread(target=server.serve, daemon=True)
    server_thread.start()
    try:
        client.run()
    finally:
        print("rpc_server 退出", flush=True)


if __name__ == "__main__":
    main()
