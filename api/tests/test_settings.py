import unittest

from src.core import settings as app_settings


class SettingsTest(unittest.TestCase):
    def test_defaults(self):
        values = app_settings.get_all()
        self.assertEqual(values["hotkey"], "f8")
        self.assertEqual(values["active_model"], "sensevoice")
        self.assertEqual(values["chunk_ms"], "600")

    def test_roundtrip(self):
        app_settings.set("hotkey", "ctrl+shift+f8")
        self.assertEqual(app_settings.get("hotkey"), "ctrl+shift+f8")
        app_settings.set("chunk_ms", 960)
        self.assertEqual(app_settings.get("chunk_ms"), "960")
        self.assertIn("updated_at", self._raw("hotkey"))

    @staticmethod
    def _raw(key):
        from src.core.db import get_conn

        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return dict(row)
