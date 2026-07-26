"""系统托盘图标模块

使用 pystray + Pillow 在 Windows 通知区域显示图标，
支持空闲/录音中/处理中三种状态的颜色变化和气泡通知。

注意: 这是托盘模块的唯一副本。如果需要给 desktop/ 下的
HTTP API 版也加上托盘，复制此文件过去即可。
"""

import threading

import pystray
from PIL import Image, ImageDraw

# 状态 → 图标颜色 (R, G, B)
_COLORS = {
    "loading": (33, 150, 243),   # 蓝色 Material Blue 500
    "idle": (76, 175, 80),       # 绿色 Material Green 500
    "recording": (244, 67, 54),  # 红色 Material Red 500
    "processing": (255, 193, 7), # 黄色 Material Amber 500
}

# 状态 → 鼠标悬停提示文字
_STATUS_LABELS = {
    "loading": "正在加载模型中...",
    "idle": "空闲中 — 按 F8 录音",
    "recording": "录音中...",
    "processing": "处理中...",
}

_ICON_SIZE = 64  # 绘制尺寸，pystray 会自动缩放到系统要求


def _create_icon_image(state: str = "idle") -> Image.Image:
    """根据状态创建纯色圆形图标"""
    color = _COLORS.get(state, _COLORS["idle"])
    img = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    draw.ellipse(
        [margin, margin, _ICON_SIZE - margin - 1, _ICON_SIZE - margin - 1],
        fill=color + (255,),
    )
    return img


class TrayIcon:
    """系统托盘图标，在后台守护线程中运行"""

    def __init__(self, on_quit=None):
        """
        Args:
            on_quit: 用户点击"退出"菜单时的回调，应设置 _running = False
        """
        self._on_quit = on_quit
        self._state = "idle"
        self._icon = None
        self._thread = None

    def _build_menu(self):
        """构建右键菜单：状态文字 + 分隔线 + 退出"""
        label = _STATUS_LABELS.get(self._state, self._state)
        return pystray.Menu(
            pystray.MenuItem(label, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit_clicked),
        )

    def _on_quit_clicked(self):
        """用户点击退出：通知主线程退出，然后停止托盘"""
        if self._on_quit:
            self._on_quit()
        self.stop()

    def set_state(self, state: str):
        """更新托盘图标（线程安全）

        Args:
            state: "idle" | "recording" | "processing"
        """
        self._state = state
        if self._icon is not None:
            try:
                self._icon.icon = _create_icon_image(state)
                self._icon.title = _STATUS_LABELS.get(state, state)
                self._icon.menu = self._build_menu()
            except Exception:
                pass  # 托盘不可用时静默忽略

    def notify(self, text: str, title: str = "语音输入"):
        """弹出 Windows 气泡通知显示识别结果"""
        if self._icon is not None:
            try:
                self._icon.notify(text, title)
            except Exception:
                pass

    def _run_loop(self):
        """pystray 事件循环（阻塞，在守护线程中运行）"""
        self._icon = pystray.Icon(
            "phonetics-asr",
            _create_icon_image("idle"),
            "语音输入客户端",
            menu=self._build_menu(),
        )
        self._icon.run()

    def start(self):
        """启动托盘线程"""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止托盘图标（幂等，可重复调用）"""
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
