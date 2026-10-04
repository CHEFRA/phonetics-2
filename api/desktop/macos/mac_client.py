"""macOS 终端版语音输入客户端

与 Windows 版(desktop/asr_client.py)平行的独立实现,共享
audio_recorder 与 src/ 下的模型推理、历史入库代码。

为什么单独实现: pystray 的 darwin 后端要求 AppKit 主线程运行事件
循环,与 Windows 版"托盘在守护线程、主线程跑推理轮询"的模型相反;
为避免触碰 Windows 路径,这里按 macOS 线程模型独立实现:
- 主线程: 菜单栏托盘事件循环(AppKit)
- worker 线程: 加载模型、轮询待识别音频、推理、历史入库、粘贴
- pynput Listener 自带线程: 全局热键监听

权限要求(授权对象为运行本程序的终端 App,详见 permissions.py):
辅助功能(粘贴)、输入监控(热键)、麦克风(录音)。

启动方式(在 api 目录下):
    uv run python -m desktop.macos.mac_client
或双击 scripts/phonetics-asr-mac.command
"""

import logging
import os
import platform
import sys
import tempfile
import threading
import time

import psutil

from src.core.logger import make_console_safe

# 日志写入临时目录,方便后台/无窗口场景排查
_log_file = os.path.join(tempfile.gettempdir(), "phonetics-asr-mac.log")
logging.basicConfig(
    filename=_log_file,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True,
)

make_console_safe()


def _log_exception(exc_type, exc_value, exc_traceback):
    """捕获主线程未处理的异常并写入日志"""
    logging.error("未捕获的异常", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = _log_exception

import pynput
import pyperclip
import scipy.io.wavfile as wavfile
from pynput import keyboard

# 先 import config 以加载 api/.env,之后才能读到 HOTKEY 配置
import src.core.config  # noqa: F401
from desktop.audio_recorder import AudioRecorder
from desktop.macos.permissions import warn_if_restricted
from desktop.macos.tray_bar import TrayBar
from src.core.db import init_db
from src.services import history
from src.services.sensevoice import sensevoice_service

try:
    from importlib.metadata import version as _pkg_version

    _APP_VERSION = _pkg_version("api")
except Exception:
    _APP_VERSION = None

PASTE_KEY = keyboard.Key.cmd  # macOS 粘贴键
PASTE_DELAY = 0.618  # 粘贴前等待时间(秒),避开热键释放

# 热键: 默认 f8,可在 api/.env 中用 HOTKEY 修改,如 HOTKEY=ctrl+shift+space
# 注意 Mac 键盘 F8 默认是媒体键,直接按需同时按 fn,或在系统设置开启
# "将 F1、F2 等键用作标准功能键";不便时可改用组合键
_HOTKEY_ALIASES = {
    "ctrl": keyboard.Key.ctrl,
    "control": keyboard.Key.ctrl,
    "shift": keyboard.Key.shift,
    "alt": keyboard.Key.alt,
    "option": keyboard.Key.alt,
    "cmd": keyboard.Key.cmd,
    "command": keyboard.Key.cmd,
    "space": keyboard.Key.space,
    "esc": keyboard.Key.esc,
    "tab": keyboard.Key.tab,
    "enter": keyboard.Key.enter,
    "return": keyboard.Key.enter,
}

_HOTKEY_NAMES = {
    keyboard.Key.ctrl: "Ctrl",
    keyboard.Key.shift: "Shift",
    keyboard.Key.alt: "Option",
    keyboard.Key.cmd: "Cmd",
    keyboard.Key.space: "Space",
    keyboard.Key.esc: "Esc",
    keyboard.Key.tab: "Tab",
    keyboard.Key.enter: "Enter",
}


def _parse_hotkey(spec: str) -> set:
    """解析热键配置字符串,如 "f8" / "ctrl+shift+space",返回按键集合"""
    keys = set()
    for part in (p.strip().lower() for p in spec.split("+")):
        if not part:
            continue
        if part in _HOTKEY_ALIASES:
            keys.add(_HOTKEY_ALIASES[part])
        elif part.startswith("f") and part[1:].isdigit() and 1 <= int(part[1:]) <= 20:
            keys.add(getattr(keyboard.Key, part))
        elif len(part) == 1:
            keys.add(keyboard.KeyCode.from_char(part))
        else:
            raise ValueError(f"无法识别的热键片段: {part!r}")
    if not keys:
        raise ValueError("热键配置为空")
    return keys


def _hotkey_label(keys: set) -> str:
    """把按键集合还原成可读文案,用于启动提示"""
    parts = []
    for key in keys:
        if key in _HOTKEY_NAMES:
            parts.append(_HOTKEY_NAMES[key])
        elif isinstance(key, keyboard.KeyCode) and key.char:
            parts.append(key.char.upper())
        else:
            parts.append(getattr(key, "name", str(key)).capitalize())
    return "+".join(parts)


try:
    HOTKEY_KEYS = _parse_hotkey(os.getenv("HOTKEY", "f8"))
except Exception:
    logging.error("HOTKEY 配置无效,回退默认 f8", exc_info=True)
    HOTKEY_KEYS = {keyboard.Key.f8}


class MacASRClient:
    """语音输入客户端(macOS): 主线程跑菜单栏,推理在 worker 线程"""

    def __init__(self):
        self.recorder = AudioRecorder()
        self.state = "idle"  # idle -> recording -> processing -> idle
        self.listener = None
        self._pressed_keys: set = set()
        self._trigger_lock = False
        self._running = True
        self._pending_audio = None
        self.session_id = None
        self._record_start_time = 0.0
        self._record_duration = 0.0
        self.tray = None
        self._cleaned = False

    # ---- 状态与退出 ----

    def _on_tray_quit(self):
        """托盘菜单"退出"点击回调(主线程)"""
        self._running = False

    def _set_state(self, state: str):
        """统一设置状态并同步菜单栏图标(线程安全)"""
        self.state = state
        if self.tray:
            self.tray.set_state(state)

    # ---- 全局热键(pynput Listener 自带线程) ----

    def _on_press(self, key):
        """按键按下回调"""
        try:
            if key == keyboard.Key.esc:
                if self.state == "recording":
                    self._cancel_recording()
                return

            self._pressed_keys.add(key)
            if HOTKEY_KEYS.issubset(self._pressed_keys) and not self._trigger_lock:
                self._trigger_lock = True
                self._toggle_recording()
        except Exception:
            logging.error("按键处理异常", exc_info=True)

    def _on_release(self, key):
        """按键释放回调"""
        try:
            self._pressed_keys.discard(key)
            if not HOTKEY_KEYS.intersection(self._pressed_keys):
                self._trigger_lock = False
        except Exception:
            logging.error("按键处理异常", exc_info=True)

    def _start_listener(self):
        """启动全局热键监听(主线程调用,pynput 在自己的线程里收发事件)"""
        self.listener = pynput.keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self.listener.start()
        logging.info("热键监听已启动")

    # ---- 录音状态机 ----

    def _toggle_recording(self):
        """切换录音状态"""
        if self.state == "idle":
            self._start_recording()
        elif self.state == "recording":
            self._stop_recording()
        elif self.state == "processing":
            pass
        else:
            print("未知状态")

    def _start_recording(self):
        """开始录音"""
        self._set_state("recording")
        self._record_start_time = time.time()
        self._record_duration = 0.0
        self.recorder.start()
        print("录音中...")

    def _stop_recording(self):
        """停止录音"""
        print("停止录音")
        audio_data = self.recorder.stop()

        record_duration = time.time() - self._record_start_time
        self._record_duration = record_duration
        print(f"录音时长: {record_duration:.2f}秒")

        if len(audio_data) == 0:
            print("录音为空")
            logging.warning("录音为空")
            history.record_transcription(
                session_id=self.session_id,
                source="desktop",
                model=sensevoice_service.model_id,
                text="",
                status="empty",
                audio_duration_ms=int(record_duration * 1000),
            )
            return

        logging.info(
            f"录音完成, 时长={record_duration:.2f}s, 采样数={len(audio_data)}"
        )
        self._pending_audio = audio_data

    def _cancel_recording(self):
        """取消当前录音,丢弃音频,回到空闲"""
        self.recorder.stop()
        self._pending_audio = None
        self._record_duration = 0.0
        self._set_state("idle")
        print("已取消录音")
        logging.info("录音已取消")

    # ---- 识别与粘贴(worker 线程) ----

    def _recognize(self, wav_path: str):
        """直接调用本地模型识别音频

        返回 (文本, 状态, 错误, 推理耗时ms, 推理前内存MB, 推理后内存MB)
        """
        proc = psutil.Process(os.getpid())
        mem_before_mb = proc.memory_info().rss / 1024 / 1024
        start_time = time.time()
        try:
            text = sensevoice_service.recognize(wav_path)
        except Exception as e:
            inference_ms = int((time.time() - start_time) * 1000)
            mem_after_mb = proc.memory_info().rss / 1024 / 1024
            print(f"识别出错: {e}")
            logging.error("识别异常", exc_info=True)
            return "", "error", str(e), inference_ms, mem_before_mb, mem_after_mb

        inference_ms = int((time.time() - start_time) * 1000)
        mem_after_mb = proc.memory_info().rss / 1024 / 1024
        print(f"识别时长: {inference_ms / 1000:.2f}秒")
        logging.info(f"识别完成, 时长={inference_ms}ms, text='{text[:50]}'")
        status = "success" if text else "empty"
        return text, status, None, inference_ms, mem_before_mb, mem_after_mb

    def _paste_to_focus(self, text: str):
        """将文本粘贴到焦点窗口(需要辅助功能权限)"""
        try:
            original = pyperclip.paste()
        except Exception:
            original = ""

        pyperclip.copy(text)
        time.sleep(0.1)

        kb = pynput.keyboard.Controller()
        time.sleep(0.1)

        kb.press(PASTE_KEY)
        time.sleep(0.05)
        kb.press("v")
        time.sleep(0.05)
        kb.release("v")
        time.sleep(0.05)
        kb.release(PASTE_KEY)

        time.sleep(0.3)

        try:
            pyperclip.copy(original)
        except Exception:
            pass

    def _process(self, audio_data):
        """保存临时 wav → 识别 → 历史入库 → 通知与粘贴"""
        self._set_state("processing")
        logging.info(f"开始处理音频, 采样数={len(audio_data)}")

        # 保存临时 wav 文件(模型需要文件路径输入)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav = f.name

        try:
            wavfile.write(temp_wav, AudioRecorder.SAMPLERATE, audio_data)
            text, status, error, inference_ms, mem_before_mb, mem_after_mb = (
                self._recognize(temp_wav)
            )
            audio_duration_ms = int(self._record_duration * 1000)
            rtf = (
                round(inference_ms / audio_duration_ms, 4)
                if audio_duration_ms > 0
                else None
            )
            history.record_transcription(
                session_id=self.session_id,
                source="desktop",
                model=sensevoice_service.model_id,
                text=text,
                status=status,
                error=error,
                audio_duration_ms=audio_duration_ms,
                inference_ms=inference_ms,
                rtf=rtf,
                mem_before_mb=round(mem_before_mb, 1),
                mem_after_mb=round(mem_after_mb, 1),
            )
            if text:
                if self.tray:
                    self.tray.notify(text, "语音识别结果")
                time.sleep(PASTE_DELAY)  # 避开热键释放
                self._paste_to_focus(text)
                print(f"识别成功: {text}")
            else:
                print("识别失败")
        finally:
            os.unlink(temp_wav)

        self._set_state("idle")

    def _worker(self):
        """加载模型并轮询待识别音频(独立线程,主线程留给 AppKit)"""
        try:
            self._set_state("loading")
            print("正在加载模型...")
            logging.info("开始加载模型")
            sensevoice_service.get_model()
            self._set_state("idle")
            logging.info("模型加载完成")
            print(f"监听中,按 {_hotkey_label(HOTKEY_KEYS)} 开始/停止录音,按 Esc 取消录音")

            while self._running:
                if self._pending_audio is not None:
                    audio_data = self._pending_audio
                    self._pending_audio = None
                    try:
                        self._process(audio_data)
                    except Exception:
                        logging.error("处理音频异常", exc_info=True)
                        self._set_state("idle")
                time.sleep(0.1)
        except Exception:
            logging.error("worker 异常退出", exc_info=True)
        finally:
            if self.tray:
                self.tray.request_stop()

    # ---- 生命周期 ----

    def _cleanup(self):
        """清理资源(幂等,可被正常退出与 terminate 兜底两条路径调用)"""
        if self._cleaned:
            return
        self._cleaned = True
        if self.session_id:
            history.end_session(self.session_id)
        if self.recorder._stream is not None:
            try:
                self.recorder.stop()
            except Exception:
                pass
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass

    def run(self):
        """启动客户端,阻塞主线程于菜单栏事件循环直到退出"""
        init_db()
        self.session_id = history.start_session(
            app="desktop",
            version=_APP_VERSION,
            device=platform.platform(),
            model=sensevoice_service.model_id,
        )
        warn_if_restricted()
        self.tray = TrayBar(on_quit=self._on_tray_quit)
        worker = threading.Thread(target=self._worker, daemon=True, name="asr-worker")
        worker.start()
        # 必须在进入 AppKit 循环之前启动热键监听: pynput 初始化时查询键盘
        # 输入源(HIToolbox),若与 NSApp.run() 并发启动会触发输入源列表
        # 为空的断言崩溃(_HaveOnlyOneKeyboardInputSource → SIGABRT)
        self._start_listener()
        # 主线程进入 AppKit 菜单栏循环(阻塞直到退出);
        # Ctrl+C 由 pystray darwin 后端接管,经 on_terminate 兜底清理后退出
        self.tray.run(on_terminate=self._cleanup)
        # 无论菜单退出还是 Ctrl+C,统一在这里收尾
        self._running = False
        worker.join(timeout=10)
        self._cleanup()
        print("已退出")


def main():
    MacASRClient().run()


if __name__ == "__main__":
    main()
