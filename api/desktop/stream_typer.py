"""流式文本实时打字器

把流式 ASR 的 partial 文本打进当前焦点窗口：
  - 新文本是旧文本的追加时，只输入新增后缀（快路径）
  - 发生修订时，先删除已打字内容再重新输入
  - 说话结束时 clear() 删除 partial，由调用方粘贴最终文本

Windows 下所有字符通过 SendInput KEYEVENTF_UNICODE 输入，
可绕过输入法（IME）组合，中英文混打不会进入拼音候选；
其他平台回退到 pynput 逐字符输入。
"""

import platform
import time

from pynput import keyboard

_CHAR_DELAY = 0.012  # 每字符间隔，防止过快丢字
_BACKSPACE_DELAY = 0.008

_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT)]

    class _INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]

    _KEYEVENTF_UNICODE = 0x0004
    _KEYEVENTF_KEYUP = 0x0002

    def _send_unicode_unit(unit: int, key_up: bool):
        """发送一个 UTF-16 码元的 Unicode 键盘事件"""
        flags = _KEYEVENTF_UNICODE | (_KEYEVENTF_KEYUP if key_up else 0)
        inp = _INPUT(
            type=1,  # INPUT_KEYBOARD
            union=_INPUTUNION(
                ki=_KEYBDINPUT(
                    wVk=0,
                    wScan=unit,
                    dwFlags=flags,
                    time=0,
                    dwExtraInfo=None,
                )
            ),
        )
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

    def _type_text_unicode(text: str):
        """逐字符发送 Unicode 输入事件（Windows，绕过 IME）"""
        for ch in text:
            code = ord(ch)
            if code <= 0xFFFF:
                units = [code]
            else:
                # 超出 BMP 的字符拆成代理对（表情等）
                code -= 0x10000
                units = [0xD800 + (code >> 10), 0xDC00 + (code & 0x3FF)]
            for unit in units:
                _send_unicode_unit(unit, key_up=False)
                _send_unicode_unit(unit, key_up=True)
            time.sleep(_CHAR_DELAY)


class StreamTyper:
    """维护“屏幕上已打出的流式文本”，支持追加、替换、清理"""

    def __init__(self):
        self.typed = ""
        self._kb = keyboard.Controller()

    def reset(self):
        """新一轮说话开始前调用（屏幕上旧文本由调用方负责清理）"""
        self.typed = ""

    def update(self, text: str):
        """用新 partial 同步屏幕文本

        新文本是旧文本追加时只输入后缀；否则整体替换。
        """
        text = text or ""
        if text == self.typed:
            return
        if text.startswith(self.typed):
            self._type(text[len(self.typed) :])
        else:
            self._backspace(len(self.typed))
            if text:
                self._type(text)
        self.typed = text

    def clear(self):
        """删除屏幕上已打出的 partial（结束替换或取消时调用）"""
        self._backspace(len(self.typed))
        self.typed = ""

    def _backspace(self, count: int):
        for _ in range(count):
            self._kb.press(keyboard.Key.backspace)
            self._kb.release(keyboard.Key.backspace)
            time.sleep(_BACKSPACE_DELAY)

    def _type(self, text: str):
        if not text:
            return
        if _IS_WINDOWS:
            _type_text_unicode(text)
        else:
            for ch in text:
                self._kb.press(ch)
                self._kb.release(ch)
                time.sleep(_CHAR_DELAY)
