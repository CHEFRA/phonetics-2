"""语音输入客户端主程序（直接调用本地模型）

支持两种交互：
  - 整段模式（SenseVoice）：F8 开始录音，再按 F8 停止，识别后粘贴
  - 流式模式（paraformer-streaming）：F8 开始监听，说话过程中实时往
    焦点窗口打字，再按 F8 停止，最终文本（补标点）替换屏幕上的 partial

按 Esc 取消本次录音/监听。
"""

import logging
import os
import platform
import sys
import tempfile
import threading
import time
from pathlib import Path

import psutil

from src.core.logger import make_console_safe

# 日志配置（写入临时目录，方便 pythonw 模式下排查）
_log_file = os.path.join(tempfile.gettempdir(), "phonetics-asr.log")
logging.basicConfig(
    filename=_log_file,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True,
)

make_console_safe()


def _log_exception(exc_type, exc_value, exc_traceback):
    """捕获未处理的异常并写入日志"""
    logging.error("未捕获的异常", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = _log_exception

import pynput
import pyperclip
import scipy.io.wavfile as wavfile
from pynput import keyboard

from audio_recorder import AudioRecorder
from hotkey import canonical_hotkey, parse_hotkey
from stream_typer import StreamTyper
from src.core import config
from src.core import settings as app_settings
from src.core.asr_registry import (
    get_active_model_name,
    get_asr_service,
    get_model_dir,
    set_active_model,
    set_model_dir,
    set_punc_model_dir,
)
from src.core.db import init_db
from src.services import history

try:
    from tray_icon import TrayIcon

    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# 平台配置
IS_MAC = platform.system() == "Darwin"
PASTE_KEY = keyboard.Key.cmd if IS_MAC else keyboard.Key.ctrl
PASTE_DELAY = 0.618  # 粘贴前等待时间（秒），用于避开热键释放

try:
    from importlib.metadata import version as _pkg_version

    _APP_VERSION = _pkg_version("api")
except Exception:
    _APP_VERSION = None

# 默认热键（可在设置页修改并持久化到 settings 表）
DEFAULT_HOTKEY = "f8"

# 模型下载映射：UI 名称 -> (本地目录名, ModelScope 仓库 ID, 注册表名, 设置键)
_MODEL_DOWNLOADS = {
    "sensevoice": (
        "SenseVoiceSmall",
        "iic/SenseVoiceSmall",
        "sensevoice",
        "model_dir_sensevoice",
    ),
    "paraformer-streaming": (
        "paraformer-zh-streaming",
        "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online",
        "paraformer-streaming",
        "model_dir_streaming",
    ),
    "ct-punc": (
        "ct-punc",
        "iic/punc_ct-transformer_cn-en-common-vocab471067-large",
        "ct-punc",
        "model_dir_punc",
    ),
}

# 当前 ASR 引擎（由环境变量 ASR_MODEL 决定，不触发模型加载）
asr_service = get_asr_service()


class ASRClient:
    """语音输入客户端"""

    def __init__(self, use_tray: bool = True, event_sink=None, rpc_mode: bool = False):
        global asr_service
        self.recorder = AudioRecorder()
        self.typer = StreamTyper()
        self.state = "idle"  # idle -> recording/streaming -> processing -> idle
        self.listener = None
        self._pressed_keys: set = set()
        self._trigger_lock = False
        self._running = True
        self._pending_audio = None
        self._pending_tail = None
        self._pending_finalize = False
        self.session_id = None
        self._record_duration = 0.0
        self._stream_text = ""
        self._stream_inference_ms = 0
        self.rpc_mode = rpc_mode
        self._event_sink = (
            event_sink if callable(event_sink) else (lambda event, data: None)
        )
        # 从 settings 恢复热键、模型与运行参数
        saved = app_settings.get_all()
        self.hotkey_spec = saved.get("hotkey") or DEFAULT_HOTKEY
        self.hotkey_keys = parse_hotkey(self.hotkey_spec)
        for key, name in (
            ("model_dir_sensevoice", "sensevoice"),
            ("model_dir_streaming", "paraformer-streaming"),
        ):
            if saved.get(key):
                set_model_dir(name, saved[key])
        if saved.get("model_dir_punc"):
            set_punc_model_dir(saved["model_dir_punc"])
        saved_model = saved.get("active_model")
        if saved_model and saved_model != get_active_model_name():
            set_active_model(saved_model)
            asr_service = get_asr_service()
        try:
            config.ASR_STREAM_CHUNK_MS = int(
                saved.get("chunk_ms") or config.ASR_STREAM_CHUNK_MS
            )
        except ValueError:
            pass
        config.ASR_PUNC = str(saved.get("punc", "true")).lower() in (
            "1", "true", "yes", "on",
        )
        self._chunk_samples = (
            asr_service.chunk_samples
            if hasattr(asr_service, "chunk_samples")
            else int(AudioRecorder.SAMPLERATE * 0.6)
        )
        self.tray = (
            TrayIcon(on_quit=self._on_tray_quit)
            if use_tray and HAS_TRAY
            else None
        )

    @property
    def is_streaming_model(self) -> bool:
        """当前引擎是否走流式交互"""
        return asr_service.mode == "stream"

    def _on_tray_quit(self):
        """托盘菜单"退出"点击回调"""
        self._running = False

    def _emit(self, event, data=None):
        """推送事件给 Electron（RPC 模式）或日志"""
        try:
            self._event_sink(event, data)
        except Exception:
            logging.error("事件回调异常: %s", event, exc_info=True)

    def _listener_alive(self) -> bool:
        return self.listener is not None and self.listener.is_alive()

    def _restart_listener(self):
        """热键变更后重建全局监听器（先启动新监听器再停旧监听器）"""
        if not self._running:
            return
        new_listener = pynput.keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        new_listener.start()
        old = self.listener
        self.listener = new_listener
        if old is not None:
            try:
                old.stop()
            except Exception:
                pass

    def set_hotkey(self, spec: str):
        """设置并持久化全局热键"""
        keys = parse_hotkey(spec)
        self.hotkey_keys = keys
        self.hotkey_spec = canonical_hotkey(spec)
        app_settings.set("hotkey", self.hotkey_spec)
        self._restart_listener()
        self._emit("hotkey_changed", {"hotkey": self.hotkey_spec})

    def set_model(self, name: str):
        """运行时切换识别引擎（不加载模型，首次使用才加载）"""
        global asr_service
        if self.state in ("recording", "streaming", "processing"):
            raise RuntimeError("录音或识别中不能切换模型")
        set_active_model(name)
        asr_service = get_asr_service()
        app_settings.set("active_model", name)
        self._emit("model_changed", {"model": name, "mode": asr_service.mode})

    def set_model_dir(self, key: str, path: str):
        """设置模型目录并持久化（key: model_dir_sensevoice/streaming/punc）"""
        global asr_service
        if key == "model_dir_punc":
            set_punc_model_dir(path)
        elif key == "model_dir_sensevoice":
            set_model_dir("sensevoice", path)
        elif key == "model_dir_streaming":
            set_model_dir("paraformer-streaming", path)
        else:
            raise ValueError(f"未知模型目录设置项: {key}")
        app_settings.set(key, path)
        asr_service = get_asr_service()
        self._emit("settings_changed", {key: path})

    def set_chunk_ms(self, ms: int):
        """设置流式 chunk 粒度并持久化"""
        if not (120 <= ms <= 2000):
            raise ValueError("chunk 粒度需在 120-2000ms 之间")
        config.ASR_STREAM_CHUNK_MS = ms
        self._chunk_samples = int(AudioRecorder.SAMPLERATE * ms / 1000)
        app_settings.set("chunk_ms", str(ms))
        self._emit("settings_changed", {"chunk_ms": ms})

    def set_punc(self, enabled: bool):
        """设置流式最终文本是否补标点"""
        config.ASR_PUNC = enabled
        app_settings.set("punc", "true" if enabled else "false")
        self._emit("settings_changed", {"punc": enabled})

    def toggle_record(self) -> dict:
        self._toggle_recording()
        return self.get_status()

    def cancel_record(self) -> dict:
        self._cancel_recording()
        return self.get_status()

    def quit(self):
        self._running = False

    def get_status(self) -> dict:
        proc = psutil.Process(os.getpid())
        return {
            "state": self.state,
            "model": asr_service.name,
            "model_id": asr_service.model_id,
            "mode": asr_service.mode,
            "hotkey": self.hotkey_spec,
            "memory_mb": round(proc.memory_info().rss / 1048576, 1),
            "version": _APP_VERSION or "0.1.0",
            "session_id": self.session_id,
            "rpc_mode": self.rpc_mode,
            "db_path": str(config.DB_PATH),
            "models_root": str(config.MODELS_ROOT),
        }

    def get_settings(self) -> dict:
        """全部设置 + 只读路径信息"""
        result = app_settings.get_all()
        result["db_path"] = str(config.DB_PATH)
        result["models_root"] = str(config.MODELS_ROOT)
        return result

    def set_settings(self, values: dict) -> dict:
        """批量应用设置（白名单），触发对应运行时副作用"""
        allowed = {
            "hotkey", "active_model", "chunk_ms", "punc",
            "model_dir_sensevoice", "model_dir_streaming", "model_dir_punc",
        }
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"未知设置项: {', '.join(sorted(unknown))}")
        if "hotkey" in values:
            self.set_hotkey(str(values["hotkey"]))
        if "active_model" in values:
            self.set_model(str(values["active_model"]))
        if "chunk_ms" in values:
            self.set_chunk_ms(int(values["chunk_ms"]))
        if "punc" in values:
            self.set_punc(
                str(values["punc"]).lower() in ("1", "true", "yes", "on")
            )
        for key in (
            "model_dir_sensevoice", "model_dir_streaming", "model_dir_punc",
        ):
            if values.get(key):
                self.set_model_dir(key, str(values[key]))
        return self.get_settings()

    def get_history(self, limit=50, offset=0, query="", status="", model=""):
        return history.list_transcriptions(
            limit=limit, offset=offset, query=query, status=status, model=model
        )

    def get_stats(self) -> dict:
        return {
            "overview": history.overview(),
            "daily": history.daily_counts(30),
            "monthly": history.monthly_counts(12),
            "models_share": history.models_share(),
            "latency_trend": history.latency_trend(30),
        }

    def get_models(self) -> list[dict]:
        """模型状态列表（供模型管理页）"""
        entries = [
            ("sensevoice", "SenseVoice 整段识别", get_model_dir("sensevoice")),
            (
                "paraformer-streaming",
                "Paraformer 流式识别",
                get_model_dir("paraformer-streaming"),
            ),
            (
                "ct-punc",
                "流式标点补全",
                config.STREAMING_PUNC_MODEL_DIR,
            ),
        ]
        result = []
        for name, label, model_id in entries:
            local = Path(model_id)
            downloaded = local.is_dir() and any(local.iterdir())
            active = (
                name == get_active_model_name()
                if name != "ct-punc"
                else (
                    config.ASR_PUNC
                    and get_active_model_name() == "paraformer-streaming"
                )
            )
            result.append(
                {
                    "name": name,
                    "label": label,
                    "model_id": model_id,
                    "downloaded": downloaded,
                    "active": active,
                }
            )
        return result

    def download_model(self, name: str) -> dict:
        """下载模型到 MODELS_ROOT/<本地名>，进度通过事件上报"""
        global asr_service
        if name not in _MODEL_DOWNLOADS:
            raise ValueError(f"未知模型: {name!r}")
        local_name, repo_id, registry_name, settings_key = _MODEL_DOWNLOADS[name]
        target = Path(config.MODELS_ROOT) / local_name
        target.mkdir(parents=True, exist_ok=True)
        self._emit("download_started", {"model": name, "target": str(target)})

        stop_flag = threading.Event()

        def _monitor():
            while not stop_flag.is_set():
                try:
                    size = sum(
                        f.stat().st_size for f in target.rglob("*") if f.is_file()
                    )
                    self._emit(
                        "download_progress",
                        {"model": name, "downloaded_mb": round(size / 1048576, 1)},
                    )
                except Exception:
                    pass
                stop_flag.wait(1.0)

        monitor = threading.Thread(target=_monitor, daemon=True)
        monitor.start()
        try:
            from modelscope import snapshot_download

            snapshot_download(repo_id, local_dir=str(target))
        finally:
            stop_flag.set()

        if registry_name == "ct-punc":
            set_punc_model_dir(str(target))
        else:
            set_model_dir(registry_name, str(target))
        app_settings.set(settings_key, str(target))
        if registry_name == get_active_model_name():
            asr_service = get_asr_service()
        self._emit("download_finished", {"model": name, "target": str(target)})
        return {"model": name, "target": str(target)}

    def _set_state(self, state: str):
        """统一设置状态并同步托盘图标"""
        self.state = state
        if self.tray:
            self.tray.set_state(state)
        self._emit("state", {"state": state})

    def _on_press(self, key):
        """按键按下回调"""
        try:
            if key == keyboard.Key.esc:
                if self.state in ("recording", "streaming"):
                    self._cancel_recording()
                return

            self._pressed_keys.add(key)
            if self.hotkey_keys.issubset(self._pressed_keys) and not self._trigger_lock:
                self._trigger_lock = True
                self._toggle_recording()
        except Exception:
            logging.error("按键处理异常", exc_info=True)

    def _on_release(self, key):
        """按键释放回调"""
        try:
            self._pressed_keys.discard(key)
            if not self.hotkey_keys.intersection(self._pressed_keys):
                self._trigger_lock = False
        except Exception:
            logging.error("按键处理异常", exc_info=True)

    def _toggle_recording(self):
        """切换监听/录音状态"""
        if self.state == "idle":
            self._start_recording()
        elif self.state in ("recording", "streaming"):
            self._stop_recording()
        elif self.state == "processing":
            pass
        else:
            print("未知状态")

    def _start_recording(self):
        """开始录音/监听"""
        streaming = self.is_streaming_model
        self._set_state("streaming" if streaming else "recording")
        self._emit("recording_started", {"mode": asr_service.mode})
        self._record_start_time = time.time()
        self._record_duration = 0.0
        self._stream_text = ""
        self._stream_inference_ms = 0
        self._pending_tail = None
        self._pending_finalize = False
        self.typer.reset()
        asr_service.reset_stream()
        if streaming:
            self.recorder.start_streaming()
            print("开始监听（流式）...")
        else:
            self.recorder.start()
            print("录音中...")

    def _stop_recording(self):
        """停止录音/监听"""
        if self.is_streaming_model:
            print("停止监听")
            self._pending_tail = self.recorder.drain_remaining()
            audio_data = self.recorder.stop()
            record_duration = time.time() - self._record_start_time
            self._record_duration = record_duration
            self._pending_audio = audio_data
            self._pending_finalize = True
            print(f"监听时长: {record_duration:.2f}秒")
            logging.info(
                f"流式监听结束, 时长={record_duration:.2f}s, "
                f"采样数={len(audio_data)}, 尾部采样数={len(self._pending_tail)}"
            )
            return

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
                model=asr_service.model_id,
                text="",
                status="empty",
                audio_duration_ms=int(record_duration * 1000),
                mode=asr_service.mode,
            )
            self._emit(
                "result",
                {
                    "text": "",
                    "status": "empty",
                    "error": None,
                    "audio_duration_ms": int(record_duration * 1000),
                    "inference_ms": 0,
                    "rtf": None,
                    "model": asr_service.model_id,
                    "mode": asr_service.mode,
                },
            )
            return

        logging.info(
            f"录音完成, 时长={record_duration:.2f}s, 采样数={len(audio_data)}"
        )
        self._pending_audio = audio_data

    def _cancel_recording(self):
        """取消当前录音/监听，丢弃音频，删除已打出的 partial，回到空闲"""
        if self.recorder._stream is not None:
            self.recorder.stop()
        self.recorder.drain_remaining()  # 丢弃未消费音频
        self._pending_audio = None
        self._pending_tail = None
        self._pending_finalize = False
        self._stream_text = ""
        self._record_duration = 0.0
        self.typer.clear()
        asr_service.reset_stream()
        self._set_state("idle")
        self._emit("recording_cancelled", None)
        print("已取消录音")
        logging.info("录音已取消")

    def _recognize(self, wav_path: str):
        """整段模式：直接调用本地模型识别音频

        返回 (文本, 状态, 错误, 推理耗时ms, 推理前内存MB, 推理后内存MB)
        """
        proc = psutil.Process(os.getpid())
        mem_before_mb = proc.memory_info().rss / 1024 / 1024
        start_time = time.time()
        try:
            text = asr_service.recognize(wav_path)
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

    def _feed_stream_chunk(self):
        """流式模式：取一块音频喂给模型，并把新 partial 打到焦点窗口"""
        chunk = self.recorder.read_chunk(self._chunk_samples)
        if chunk is None:
            return
        start_time = time.time()
        try:
            new_text = asr_service.feed(chunk)
        except Exception as e:
            self._stream_inference_ms += int((time.time() - start_time) * 1000)
            print(f"流式识别出错: {e}")
            logging.error("流式识别异常", exc_info=True)
            return
        self._stream_inference_ms += int((time.time() - start_time) * 1000)
        if new_text:
            self._stream_text += new_text
            self.typer.update(self._stream_text)
            self._emit("partial", {"text": self._stream_text})

    def _handle_stream_finalize(self):
        """流式模式：处理说话结束（冲刷尾部、补标点、替换屏幕上 partial）"""
        self._pending_finalize = False
        self._set_state("processing")

        tail = self._pending_tail
        self._pending_tail = None
        audio_data = self._pending_audio
        self._pending_audio = None
        audio_duration_ms = int(self._record_duration * 1000)

        proc = psutil.Process(os.getpid())
        mem_before_mb = proc.memory_info().rss / 1024 / 1024
        start_time = time.time()
        text = ""
        error = None
        status = "success"
        try:
            tail_text = ""
            if tail is not None and len(tail) > 0:
                tail_text = asr_service.feed(tail, is_final=True)
            text = asr_service.punctuate(self._stream_text + tail_text)
        except Exception as e:
            error = str(e)
            status = "error"
            print(f"流式识别出错: {e}")
            logging.error("流式识别异常", exc_info=True)

        self._stream_inference_ms += int((time.time() - start_time) * 1000)
        inference_ms = self._stream_inference_ms
        mem_after_mb = proc.memory_info().rss / 1024 / 1024
        self._stream_text = ""

        # 先删除屏幕上的 partial，再粘贴最终文本
        self.typer.clear()

        if status == "success" and not text:
            status = "empty"

        rtf = (
            round(inference_ms / audio_duration_ms, 4)
            if audio_duration_ms > 0
            else None
        )
        history.record_transcription(
            session_id=self.session_id,
            source="desktop",
            model=asr_service.model_id,
            text=text,
            status=status,
            error=error,
            audio_duration_ms=audio_duration_ms,
            inference_ms=inference_ms,
            rtf=rtf,
            mem_before_mb=round(mem_before_mb, 1),
            mem_after_mb=round(mem_after_mb, 1),
            mode="stream",
        )
        self._emit(
            "result",
            {
                "text": text,
                "status": status,
                "error": error,
                "audio_duration_ms": audio_duration_ms,
                "inference_ms": inference_ms,
                "rtf": rtf,
                "model": asr_service.model_id,
                "mode": "stream",
            },
        )

        if text and status == "success":
            if self.tray:
                self.tray.notify(text, "语音识别结果")
            time.sleep(PASTE_DELAY)  # 避开热键释放
            self._paste_to_focus(text)
            print(f"识别成功: {text}")
        else:
            print("识别失败" if status == "error" else "识别为空")
        self._set_state("idle")

    def _handle_batch_processing(self):
        """整段模式：把录音写到临时 wav 并识别，粘贴结果"""
        audio_data = self._pending_audio
        self._pending_audio = None
        self._set_state("processing")
        logging.info(f"开始处理音频, 采样数={len(audio_data)}")

        # 保存临时 wav 文件（模型需要文件路径输入）
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
                model=asr_service.model_id,
                text=text,
                status=status,
                error=error,
                audio_duration_ms=audio_duration_ms,
                inference_ms=inference_ms,
                rtf=rtf,
                mem_before_mb=round(mem_before_mb, 1),
                mem_after_mb=round(mem_after_mb, 1),
                mode=asr_service.mode,
            )
            self._emit(
                "result",
                {
                    "text": text,
                    "status": status,
                    "error": error,
                    "audio_duration_ms": audio_duration_ms,
                    "inference_ms": inference_ms,
                    "rtf": rtf,
                    "model": asr_service.model_id,
                    "mode": asr_service.mode,
                },
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

    def _paste_to_focus(self, text: str):
        """将文本粘贴到焦点窗口"""
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

    def _cleanup(self):
        """清理资源"""
        if self.session_id:
            history.end_session(self.session_id)
        if self.tray:
            self.tray.stop()
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
        """启动客户端"""
        init_db()
        self.session_id = history.start_session(
            app="desktop",
            version=_APP_VERSION,
            device=platform.platform(),
            model=asr_service.model_id,
        )
        if self.tray:
            self.tray.start()
            self.tray.set_state("loading")
        if self.rpc_mode:
            # RPC 模式：启动不加载模型，由 Electron 界面触发加载
            self._set_state("idle")
            self._emit("ready", self.get_status())
            print("RPC 模式就绪，等待 Electron 指令")
        else:
            print("正在加载模型...")
            logging.info("开始加载模型")
            asr_service.get_model()
            self._set_state("idle")
            logging.info("模型加载完成")
            print("监听中，按 F8 开始/停止，按 Esc 取消")

        try:
            self.listener = pynput.keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self.listener.start()
            while self._running and self._listener_alive():
                if self._pending_finalize:
                    self._handle_stream_finalize()
                elif self._pending_audio is not None:
                    self._handle_batch_processing()
                elif self.is_streaming_model and self.state == "streaming":
                    self._feed_stream_chunk()
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n收到 Ctrl+C，正在退出...")
        finally:
            self._cleanup()
        print("已退出")


def main():
    client = ASRClient()
    client.run()


if __name__ == "__main__":
    main()
