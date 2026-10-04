"""macOS 菜单栏托盘

pystray 的 darwin 后端基于 AppKit: icon.run() 必须占用主线程的
NSApplication 事件循环,且不支持 run_detached。AppKit 的 UI 更新
要求主线程,因此本模块做两层设计:

- 对外 API(set_state/notify/request_stop)在任意线程只做入队
- 真正调用 pystray/AppKit 的操作由主线程 NSTimer 事件泵执行

事件泵的挂载点: pystray 的 setup 回调运行在它自己的辅助线程上,
不能用来调度 NSTimer;而 darwin 后端的 _mark_ready 在主线程、
NSApp.run() 之前被调用,因此用 pystray.Icon 子类在 _mark_ready 里
把 NSTimer 挂到主 run loop(见 _PumpedIcon)。

与 Windows 托盘(tray_icon.py)的呈现差异:
- macOS 菜单栏没有悬停提示(setToolTip 在部分 macOS 版本不生效),
  "状态 + 实时内存"同时写入下拉菜单第一项
- 下拉菜单是打开时的静态快照,事件泵每 2 秒重建一次以刷新内容
- 通知走 osascript 的 display notification,未打包进程下更可靠
"""

import logging
import os
import queue
import subprocess
import time

import psutil
import pystray
from PIL import Image, ImageDraw

try:
    import Foundation
except ImportError:  # pragma: no cover - pystray darwin 必带 pyobjc,仅防御
    Foundation = None

# 状态 → 图标颜色 (R, G, B),与 Windows 托盘保持一致
_COLORS = {
    "loading": (33, 150, 243),   # 蓝色 Material Blue 500
    "idle": (76, 175, 80),       # 绿色 Material Green 500
    "recording": (244, 67, 54),  # 红色 Material Red 500
    "processing": (255, 193, 7), # 黄色 Material Amber 500
}

# 状态 → 菜单第一项文字
_STATUS_LABELS = {
    "loading": "正在加载模型中...",
    "idle": "空闲中 — 按热键录音",
    "recording": "录音中...",
    "processing": "处理中...",
}

_ICON_SIZE = 64  # 绘制尺寸,系统会自动缩放到菜单栏要求
_PUMP_INTERVAL = 0.3  # 主线程事件泵间隔(秒)
_MENU_REFRESH_INTERVAL = 2.0  # 菜单与悬停提示刷新间隔(秒)


def _format_memory(mb: float) -> str:
    """把 MB 换算成易读字符串(与活动监视器"内存"列同量级)"""
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB"


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


def _osascript_quote(s: str) -> str:
    """osascript 字符串字面量转义"""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


class _TerminateDelegate(Foundation.NSObject):
    """NSApp 委托: 进程被 terminate 结束时(如 Ctrl+C)先执行 Python 侧清理

    pystray 的 SIGINT 处理直接调用 NSApp.terminate(),而 terminate 会
    exit() 整个进程,Python 的正常收尾(finally/atexit)不会执行;
    applicationShouldTerminate: 是退出前唯一稳定回调点。
    """

    callback = None

    def applicationShouldTerminate_(self, sender):
        if self.callback:
            try:
                self.callback()
            except Exception:
                logging.error("退出清理异常", exc_info=True)
        return 1  # NSTerminateNow(注意 0 是 NSTerminateCancel)


class _PumpedIcon(pystray.Icon):
    """在主线程 run loop 上挂事件泵的 pystray.Icon 子类

    darwin 后端的 _run 在主线程调用 _mark_ready 后才进入 NSApp.run(),
    在此把周期泵挂到主 run loop,是唯一稳定的主线程挂载点。
    """

    #: 由 TrayBar.run 注入,泵回调,签名 (timer) -> None
    _pump_callback = None

    #: 由 TrayBar.run 注入,terminate 退出前的清理回调
    _on_terminate = None

    def _mark_ready(self):
        super()._mark_ready()
        if self._pump_callback is not None:
            try:
                from Foundation import NSTimer

                self._pump_timer = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                    _PUMP_INTERVAL, True, self._pump_callback
                )
            except Exception:
                logging.error("托盘事件泵启动失败", exc_info=True)
        if self._on_terminate is not None and Foundation is not None:
            from AppKit import NSApplication

            delegate = _TerminateDelegate.alloc().init()
            delegate.callback = self._on_terminate
            NSApplication.sharedApplication().setDelegate_(delegate)


class TrayBar:
    """macOS 菜单栏图标。run() 需在主线程调用,其余方法线程安全(仅入队)。"""

    def __init__(self, on_quit=None):
        """
        Args:
            on_quit: 用户点击"退出"菜单时的回调,应设置 _running = False;
                托盘循环由 worker 退出后调用 request_stop() 结束
        """
        self._on_quit = on_quit
        self._state = "loading"
        self._events: "queue.Queue[tuple]" = queue.Queue()
        self._icon = None
        self._last_refresh = 0.0

    # ---- 任意线程调用: 只入队,主线程泵执行 ----

    def set_state(self, state: str):
        """更新菜单栏图标状态(线程安全)

        Args:
            state: "loading" | "idle" | "recording" | "processing"
        """
        self._events.put(("state", state))

    def notify(self, text: str, title: str = "语音输入"):
        """弹出系统通知显示识别结果(线程安全)"""
        self._events.put(("notify", (title, text)))

    def request_stop(self):
        """请求结束托盘循环(线程安全)"""
        self._events.put(("stop", None))

    # ---- 主线程 ----

    def run(self, on_ready=None, on_terminate=None):
        """运行菜单栏 AppKit 事件循环,阻塞主线程直到 stop

        Args:
            on_ready: 事件循环就绪后回调一次(pystray 在自己的辅助线程
                上调用,可安全用于启动 pynput Listener)
            on_terminate: 进程被 NSApp.terminate 结束时(Ctrl+C)在
                applicationShouldTerminate: 阶段同步回调一次,用于兜底清理
        """
        icon = _PumpedIcon(
            "phonetics-asr",
            _create_icon_image(self._state),
            menu=self._build_menu(),
        )
        icon._pump_callback = self._drain
        icon._on_terminate = on_terminate
        self._icon = icon
        icon.run(setup=self._make_setup(on_ready))

    def _make_setup(self, on_ready):
        def setup(icon):
            icon.visible = True
            if on_ready:
                on_ready()

        return setup

    def _drain(self, timer=None):
        """主线程执行: 处理所有 UI 事件,并周期刷新菜单与悬停提示"""
        while True:
            try:
                kind, payload = self._events.get_nowait()
            except queue.Empty:
                break
            try:
                if kind == "state":
                    self._apply_state(payload)
                elif kind == "notify":
                    self._apply_notify(*payload)
                elif kind == "stop":
                    self._icon.stop()
            except Exception:
                logging.error("托盘事件处理异常", exc_info=True)

        now = time.monotonic()
        if now - self._last_refresh >= _MENU_REFRESH_INTERVAL:
            self._last_refresh = now
            try:
                self._refresh_display()
            except Exception:
                logging.error("托盘刷新异常", exc_info=True)

    def _apply_state(self, state: str):
        self._state = state
        if self._icon is not None:
            self._icon.icon = _create_icon_image(state)

    def _apply_notify(self, title: str, text: str):
        script = (
            f"display notification {_osascript_quote(text)} "
            f"with title {_osascript_quote(title)}"
        )
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            timeout=5,
        )

    def _refresh_display(self):
        """重建菜单并更新悬停提示(要求主线程)"""
        if self._icon is None:
            return
        self._icon.menu = self._build_menu()
        self._icon.title = self._status_text()

    def _build_menu(self):
        """下拉菜单: 状态+内存(只读) + 分隔线 + 退出"""
        return pystray.Menu(
            pystray.MenuItem(self._status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit_clicked),
        )

    def _status_text(self, item=None):
        """菜单第一项文字(构建时求值,配合周期重建实现实时内存)"""
        label = _STATUS_LABELS.get(self._state, self._state)
        return f"{label} | 内存 {_format_memory(self._get_memory_mb())}"

    @staticmethod
    def _get_memory_mb() -> float:
        """当前进程物理内存占用(MB)"""
        try:
            return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def _on_quit_clicked(self):
        """用户点击退出: 只置退出标志,托盘循环由 worker 收尾时结束"""
        if self._on_quit:
            self._on_quit()
