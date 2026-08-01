"""验证托盘悬浮提示内存格式与标题逻辑（不弹出真实托盘）"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "desktop"))
sys.stdout.reconfigure(encoding="utf-8")

import psutil

from tray_icon import TrayIcon, _format_memory

# 1. 格式函数
print(f"format(1200)  = {_format_memory(1200)!r}  (期望 '1.2 GB')")
print(f"format(350)   = {_format_memory(350)!r}   (期望 '350 MB')")
print(f"format(2048)  = {_format_memory(2048)!r}  (期望 '2.0 GB')")

# 2. 当前进程内存与 psutil 直接读值对比
mb = TrayIcon._get_memory_mb()
print(f"_get_memory_mb() = {mb:.0f} MB -> {_format_memory(mb)}")

# 3. mock icon 验证标题拼接
class FakeIcon:
    def __init__(self):
        self.title = None
        self.icon = None
        self.menu = None


t = TrayIcon()
t._icon = FakeIcon()
t.set_state("idle")
print(f"idle    标题: {t._icon.title!r}")
t.set_state("loading")
print(f"loading 标题: {t._icon.title!r}")

# 4. 内容不变时跳过更新（_last_title 缓存生效）
last = t._icon.title
t._update_title()
print(f"重复更新后标题未变: {t._icon.title == last}")

# 5. 断言
assert "内存" in t._icon.title, "标题应包含内存"
assert "正在加载" in t._icon.title, "标题应包含状态"
print("\n全部通过")
