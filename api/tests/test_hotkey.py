import os
import sys
import unittest

_DESKTOP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"
)
if _DESKTOP_DIR not in sys.path:
    sys.path.insert(0, _DESKTOP_DIR)

from hotkey import canonical_hotkey, parse_hotkey  # noqa: E402


class HotkeyTest(unittest.TestCase):
    def test_parse_single(self):
        keys = parse_hotkey("f8")
        self.assertEqual(len(keys), 1)

    def test_parse_combo(self):
        keys = parse_hotkey("ctrl+shift+f8")
        self.assertEqual(len(keys), 3)

    def test_parse_space_combo(self):
        keys = parse_hotkey("ctrl+alt+space")
        self.assertEqual(len(keys), 3)

    def test_canonical_normalizes_order_and_case(self):
        self.assertEqual(canonical_hotkey("Shift+CTRL+f8"), "ctrl+shift+f8")
        self.assertEqual(canonical_hotkey("ctrl+alt+space"), "ctrl+alt+space")

    def test_single_char(self):
        self.assertEqual(canonical_hotkey("ctrl+a"), "ctrl+a")

    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_hotkey("")
        with self.assertRaises(ValueError):
            parse_hotkey("not-a-key")
