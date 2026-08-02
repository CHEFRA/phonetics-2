"""流式文本实时打字器

把流式 ASR 的 partial 文本打进目标窗口：
  - F8 按下时 capture_focus() 锁定当时的焦点窗口，之后每次刷新都
    ensure_focus() 把焦点拉回该窗口（即使用户切去看日志也不受影响）
  - 文本插入使用剪贴板粘贴（与最终回填同一机制，可靠且绕过输入法）
  - 新文本是旧文本的追加时，只粘贴新增后缀；发生修订时先删旧再粘新

Windows 下通过 AttachThreadInput + SetForegroundWindow 实现焦点锁定；
其他平台退化为“粘贴到当前焦点窗口”。
"""

import platform
import time

import pyperclip
from pynput import keyboard

_BACKSPACE_DELAY = 0.004
_PASTE_SETTLE = 0.06  # 粘贴/切窗口后的稳定等待

_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    import ctypes

    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
else:
    _user32 = None
    _kernel32 = None

_PASTE_KEY = keyboard.Key.cmd if platform.system() == "Darwin" else keyboard.Key.ctrl


def _focus_window(hwnd):
    """把前台窗口切换回目标窗口（绕过 Windows 前台锁限制）"""
    if not _user32 or not hwnd:
        return
    fg = _user32.GetForegroundWindow()
    if fg == hwnd:
        return
    cur_tid = _kernel32.GetCurrentThreadId()
    fg_tid = _user32.GetWindowThreadProcessId(fg, None) if fg else 0
    target_tid = _user32.GetWindowThreadProcessId(hwnd, None)
    attached = []
    for tid in (fg_tid, target_tid):
        if tid and tid != cur_tid:
            if _user32.AttachThreadInput(cur_tid, tid, True):
                attached.append(tid)
    try:
        _user32.BringWindowToTop(hwnd)
        _user32.SetForegroundWindow(hwnd)
    finally:
        for tid in attached:
            _user32.AttachThreadInput(cur_tid, tid, False)
    time.sleep(_PASTE_SETTLE)


class StreamTyper:
    """维护“屏幕上已打出的流式文本”，支持追加、替换、清理"""

    def __init__(self):
        self.typed = ""
        self._hwnd = None
        self._kb = keyboard.Controller()

    def reset(self):
        """新一轮说话开始前调用"""
        self.typed = ""
        self._hwnd = None

    def capture_focus(self):
        """记录 F8 按下时的前台窗口，之后所有打字都回到该窗口"""
        if _IS_WINDOWS:
            self._hwnd = _user32.GetForegroundWindow()

    def ensure_focus(self):
        """把焦点拉回 F8 按下时锁定的窗口（非 Windows 下为空操作）"""
        if _IS_WINDOWS:
            _focus_window(self._hwnd)

    def update(self, text: str):
        """用新 partial 同步目标窗口文本

        新文本是旧文本追加时只粘贴后缀；否则删除旧文本后整体粘贴。
        """
        text = text or ""
        if text == self.typed:
            return
        self.ensure_focus()
        if text.startswith(self.typed):
            self._paste(text[len(self.typed) :])
        else:
            self._backspace(len(self.typed))
            self._paste(text)
        self.typed = text

    def append(self, text: str):
        """持续听写模式：直接把新识别的文本追加到目标窗口，不做任何删除

        带一个轻量去重：若新文本开头与已上屏文本的末尾重叠（chunk 边界
        模型偶发重复输出），只追加不重叠的部分。
        """
        text = text or ""
        if not text:
            return
        overlap = 0
        limit = min(4, len(self.typed), len(text))
        for k in range(1, limit + 1):
            if self.typed[-k:] == text[:k]:
                overlap = k
        text = text[overlap:]
        if not text:
            return
        self.ensure_focus()
        self._paste(text)
        self.typed += text

    def clear(self):
        """删除目标窗口里已打出的 partial（结束替换或取消时调用）"""
        if not self.typed:
            return
        self.ensure_focus()
        self._backspace(len(self.typed))
        self.typed = ""

    def replace_with(self, final_text: str):
        """用最终文本替换 partial：只回删与最终文本不一致的尾部，粘贴差异部分

        例如 partial「你好世界」→ 最终「你好，世界。」时，
        只回删「世界」再粘贴「，世界。」，避免整句闪删。
        """
        final_text = final_text or ""
        if final_text == self.typed:
            self.typed = ""
            return
        self.ensure_focus()
        prefix = 0
        limit = min(len(self.typed), len(final_text))
        while prefix < limit and self.typed[prefix] == final_text[prefix]:
            prefix += 1
        if prefix < len(self.typed):
            self._backspace(len(self.typed) - prefix)
        self._paste(final_text[prefix:])
        self.typed = ""

    def _backspace(self, count: int):
        for _ in range(count):
            self._kb.press(keyboard.Key.backspace)
            self._kb.release(keyboard.Key.backspace)
            time.sleep(_BACKSPACE_DELAY)

    def _paste(self, text: str):
        """用剪贴板粘贴文本并恢复原剪贴板（与最终回填同一机制）"""
        if not text:
            return
        try:
            original = pyperclip.paste()
        except Exception:
            original = ""
        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            self._kb.press(_PASTE_KEY)
            self._kb.press("v")
            self._kb.release("v")
            self._kb.release(_PASTE_KEY)
            time.sleep(_PASTE_SETTLE)
        finally:
            try:
                pyperclip.copy(original)
            except Exception:
                pass
