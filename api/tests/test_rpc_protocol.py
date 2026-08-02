import io
import json
import os
import sys
import time
import unittest

_DESKTOP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"
)
if _DESKTOP_DIR not in sys.path:
    sys.path.insert(0, _DESKTOP_DIR)

from rpc_protocol import RPCError, RPCServer  # noqa: E402


class FakeClient:
    def __init__(self):
        self.quited = False

    def get_status(self):
        return {"state": "idle"}

    def toggle_record(self):
        return {"state": "recording"}

    def set_hotkey(self, spec):
        return {"hotkey": spec}

    def get_history(self, **kwargs):
        return ([], 0)

    def download_model(self, name):
        raise RPCError("网络不可用")

    def quit(self):
        self.quited = True


class RPCServerTest(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.out = io.StringIO()
        self.server = RPCServer(
            self.client, stdin=io.StringIO(), stdout=self.out
        )

    def _last_message(self):
        lines = [ln for ln in self.out.getvalue().strip().splitlines() if ln]
        return json.loads(lines[-1])

    def test_request_response(self):
        self.server.handle_line(
            '{"id": 1, "method": "get_status", "params": {}}'
        )
        msg = self._last_message()
        self.assertEqual(msg["id"], 1)
        self.assertTrue(msg["ok"])
        self.assertEqual(msg["result"]["state"], "idle")

    def test_unknown_method(self):
        self.server.handle_line('{"id": 2, "method": "nope"}')
        msg = self._last_message()
        self.assertFalse(msg["ok"])
        self.assertEqual(msg["error"]["code"], "RPC_ERROR")

    def test_params_passed(self):
        self.server.handle_line(
            '{"id": 3, "method": "set_hotkey", "params": {"hotkey": "ctrl+a"}}'
        )
        msg = self._last_message()
        self.assertEqual(msg["result"]["hotkey"], "ctrl+a")

    def test_download_model_async_error_event(self):
        self.server.handle_line(
            '{"id": 4, "method": "download_model", "params": {"model": "sensevoice"}}'
        )
        msg = self._last_message()
        self.assertTrue(msg["ok"])
        self.assertTrue(msg["result"]["started"])
        time.sleep(0.2)
        self.assertIn("download_error", self.out.getvalue())

    def test_event_push(self):
        self.server.send_event("state", {"state": "recording"})
        self.assertIn('"event": "state"', self.out.getvalue())

    def test_quit(self):
        self.server.handle_line('{"id": 5, "method": "quit"}')
        self.assertTrue(self.client.quited)
