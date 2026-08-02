"""桌面端 stdio JSON-RPC 协议（与 Electron 共享）

请求:  {"id": 1, "method": "get_status", "params": {}}
响应:  {"id": 1, "ok": true, "result": ...}
       {"id": 1, "ok": false, "error": {"code": "...", "message": "..."}}
事件:  {"event": "state", "data": ...}

RPCServer 只依赖 client 的公开方法，不 import asr_client，
便于用假客户端做协议单测。
"""

import json
import logging
import sys
import threading


class RPCError(Exception):
    """业务错误，message 会原样返回给 Electron"""


class RPCServer:
    """基于 JSON lines 的 RPC 服务端"""

    def __init__(self, client, stdin=None, stdout=None):
        self.client = client
        self.stdin = stdin if stdin is not None else sys.stdin
        self.stdout = stdout if stdout is not None else sys.stdout
        self._write_lock = threading.Lock()
        self._handlers = self._build_handlers()

    def _build_handlers(self):
        client = self.client

        def get_history(params):
            return client.get_history(
                limit=int(params.get("limit", 50)),
                offset=int(params.get("offset", 0)),
                query=str(params.get("query", "") or ""),
                status=str(params.get("status", "") or ""),
                model=str(params.get("model", "") or ""),
            )

        return {
            "get_status": lambda p: client.get_status(),
            "toggle_record": lambda p: client.toggle_record(),
            "cancel_record": lambda p: client.cancel_record(),
            "set_hotkey": lambda p: client.set_hotkey(str(p.get("hotkey") or "")),
            "set_model": lambda p: client.set_model(str(p.get("model") or "")),
            "set_settings": lambda p: client.set_settings(p.get("values") or {}),
            "get_settings": lambda p: client.get_settings(),
            "get_history": get_history,
            "get_stats": lambda p: client.get_stats(),
            "get_models": lambda p: client.get_models(),
            "download_model": self._download_model,
            "quit": lambda p: client.quit(),
        }

    def _download_model(self, params):
        name = params.get("model") or ""
        if not name:
            raise RPCError("缺少 model 参数")
        thread = threading.Thread(
            target=self._run_download, args=(name,), daemon=True
        )
        thread.start()
        return {"started": True, "model": name}

    def _run_download(self, name):
        try:
            self.client.download_model(name)
        except Exception as exc:
            logging.exception("模型下载失败: %s", name)
            self.send_event(
                "download_error", {"model": name, "message": str(exc)}
            )

    def send_event(self, event, data=None):
        """推送事件给客户端（线程安全）"""
        self._write(json.dumps({"event": event, "data": data}, ensure_ascii=False))

    def _write(self, payload):
        with self._write_lock:
            self.stdout.write(payload + "\n")
            self.stdout.flush()

    def handle_line(self, line):
        """处理一行请求（测试可直接调用）"""
        try:
            msg = json.loads(line)
        except (ValueError, TypeError):
            return
        if not isinstance(msg, dict) or "method" not in msg:
            return
        method = msg["method"]
        params = msg.get("params") or {}
        request_id = msg.get("id")
        try:
            handler = self._handlers.get(method)
            if handler is None:
                raise RPCError(f"未知方法: {method}")
            result = handler(params)
        except RPCError as exc:
            self._reply(request_id, ok=False, code="RPC_ERROR", message=str(exc))
        except Exception as exc:
            logging.exception("RPC 处理异常: %s", method)
            self._reply(request_id, ok=False, code="INTERNAL", message=str(exc))
        else:
            self._reply(request_id, ok=True, result=result)

    def _reply(self, request_id, ok, result=None, code=None, message=None):
        if request_id is None:
            return
        if ok:
            payload = {"id": request_id, "ok": True, "result": result}
        else:
            payload = {
                "id": request_id,
                "ok": False,
                "error": {"code": code, "message": message},
            }
        self._write(json.dumps(payload, ensure_ascii=False))

    def serve(self):
        """阻塞读取 stdin 直到 EOF"""
        for raw in self.stdin:
            line = raw.strip()
            if line:
                self.handle_line(line)
