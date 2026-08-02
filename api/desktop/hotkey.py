"""热键配置解析与规范化

存储格式："f8"、"ctrl+shift+f8"、"ctrl+alt+space"；
解析为 pynput 键集合，供监听器与设置页共用。
"""

from pynput import keyboard

_SPECIAL_KEYS = {
    "esc": keyboard.Key.esc,
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
    "enter": keyboard.Key.enter,
    "backspace": keyboard.Key.backspace,
    "delete": keyboard.Key.delete,
    "insert": keyboard.Key.insert,
    "home": keyboard.Key.home,
    "end": keyboard.Key.end,
    "page_up": keyboard.Key.page_up,
    "page_down": keyboard.Key.page_down,
    "left": keyboard.Key.left,
    "right": keyboard.Key.right,
    "up": keyboard.Key.up,
    "down": keyboard.Key.down,
    "ctrl": keyboard.Key.ctrl,
    "ctrl_l": keyboard.Key.ctrl_l,
    "ctrl_r": keyboard.Key.ctrl_r,
    "shift": keyboard.Key.shift,
    "shift_l": keyboard.Key.shift_l,
    "shift_r": keyboard.Key.shift_r,
    "alt": keyboard.Key.alt,
    "alt_l": keyboard.Key.alt_l,
    "alt_r": keyboard.Key.alt_r,
    "cmd": keyboard.Key.cmd,
    "cmd_l": keyboard.Key.cmd_l,
    "cmd_r": keyboard.Key.cmd_r,
    "win": keyboard.Key.cmd,
    "f1": keyboard.Key.f1,
    "f2": keyboard.Key.f2,
    "f3": keyboard.Key.f3,
    "f4": keyboard.Key.f4,
    "f5": keyboard.Key.f5,
    "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7,
    "f8": keyboard.Key.f8,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
    "f11": keyboard.Key.f11,
    "f12": keyboard.Key.f12,
}

_MODIFIER_ORDER = [
    ("ctrl", keyboard.Key.ctrl),
    ("shift", keyboard.Key.shift),
    ("alt", keyboard.Key.alt),
    ("cmd", keyboard.Key.cmd),
]

_NAME_BY_KEY = {value: key for key, value in _SPECIAL_KEYS.items()}


def parse_hotkey(spec: str) -> frozenset:
    """把 'ctrl+shift+f8' 解析为 pynput 键集合"""
    parts = [part.strip().lower() for part in spec.split("+") if part.strip()]
    if not parts:
        raise ValueError("热键不能为空")
    keys = set()
    for part in parts:
        if part in _SPECIAL_KEYS:
            keys.add(_SPECIAL_KEYS[part])
        elif len(part) == 1:
            keys.add(keyboard.KeyCode.from_char(part))
        else:
            raise ValueError(f"不支持的热键: {part!r}")
    return frozenset(keys)


def canonical_hotkey(spec: str) -> str:
    """把任意书写形式规范化为 'ctrl+shift+f8' 形式"""
    keys = parse_hotkey(spec)
    parts = []
    modifier_keys = [key for _, key in _MODIFIER_ORDER]
    for name, key in _MODIFIER_ORDER:
        if key in keys:
            parts.append(name)
    for key in keys:
        if key in modifier_keys:
            continue
        if key in _NAME_BY_KEY:
            parts.append(_NAME_BY_KEY[key])
        elif hasattr(key, "char") and key.char:
            parts.append(key.char)
        else:
            parts.append(str(key))
    return "+".join(parts)
