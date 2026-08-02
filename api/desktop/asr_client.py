"""语音输入客户端主程序（直接调用本地模型）

支持两种交互：
  - 整段模式（SenseVoice）：F8 开始录音，再按 F8 停止，识别后粘贴
  - 流式模式（paraformer-streaming）：F8 开始监听，说话过程中实时往
    焦点窗口打字，再按 F8 停止，最终文本（补标点）替换屏幕上的 partial

按 Esc 取消本次录音/监听。
"""

import logging
import os
import sys
import tempfile
import time
import platform

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
from stream_typer import StreamTyper
from src.core.asr_registry import get_asr_service
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
PASTE_DELAY = 0.35  # 粘贴前等待时间（秒），用于避开热键释放

try:
    from importlib.metadata import version as _pkg_version

    _APP_VERSION = _pkg_version("api")
except Exception:
    _APP_VERSION = None

# 热键配置（修改此处即可更改快捷键）
# 单键：{keyboard.Key.f8}
# 组合键：{keyboard.Key.ctrl_l, keyboard.Key.shift_l, keyboard.Key.space}
HOTKEY_KEYS = {keyboard.Key.f8}

# 当前 ASR 引擎（由环境变量 ASR_MODEL 决定，不触发模型加载）
asr_service = get_asr_service()


class ASRClient:
    """语音输入客户端"""

    def __init__(self):
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
        self._chunk_samples = (
            asr_service.chunk_samples
            if hasattr(asr_service, "chunk_samples")
            else int(AudioRecorder.SAMPLERATE * 0.6)
        )
        self.tray = TrayIcon(on_quit=self._on_tray_quit) if HAS_TRAY else None

    @property
    def is_streaming_model(self) -> bool:
        """当前引擎是否走流式交互"""
        return asr_service.mode == "stream"

    def _on_tray_quit(self):
        """托盘菜单"退出"点击回调"""
        self._running = False

    def _set_state(self, state: str):
        """统一设置状态并同步托盘图标"""
        self.state = state
        if self.tray:
            self.tray.set_state(state)

    def _on_press(self, key):
        """按键按下回调"""
        try:
            if key == keyboard.Key.esc:
                if self.state in ("recording", "streaming"):
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
        self._record_start_time = time.time()
        self._record_duration = 0.0
        self._stream_text = ""
        self._stream_inference_ms = 0
        self._pending_tail = None
        self._pending_finalize = False
        self.typer.reset()
        self.typer.capture_focus()  # 锁定 F8 按下时的焦点窗口
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
                f"尾部采样数={len(self._pending_tail)}"
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
            return

        logging.info(
            f"录音完成, 时长={record_duration:.2f}s, 采样数={len(audio_data)}"
        )
        self._pending_audio = audio_data

    def _cancel_recording(self):
        """停止监听并丢弃尾部音频；已输出的文字保留在屏幕上"""
        if self.recorder._stream is not None:
            self.recorder.stop()
        self.recorder.drain_remaining()  # 丢弃未冲刷的尾部音频
        self._pending_audio = None
        self._pending_tail = None
        self._pending_finalize = False
        self._stream_text = ""
        self._record_duration = 0.0
        asr_service.reset_stream()
        self._set_state("idle")
        print("已停止监听（已输出的文字保留）")
        logging.info("监听已取消，已输出文字保留")

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
            self.typer.append(new_text)
            print(f"+ {new_text}")
            logging.info(f"流式增量: {new_text!r}")

    def _handle_stream_stop(self):
        """持续听写模式：停止监听，冲刷尾部音频并追加最后一段文本

        不做标点、不做整段替换——屏幕上已有的文字就是最终文字。
        """
        self._pending_finalize = False
        self._set_state("processing")
        print("正在冲刷尾部...")

        tail = self._pending_tail
        self._pending_tail = None
        self._pending_audio = None
        audio_duration_ms = int(self._record_duration * 1000)

        proc = psutil.Process(os.getpid())
        mem_before_mb = proc.memory_info().rss / 1024 / 1024
        start_time = time.time()
        text = self._stream_text
        error = None
        status = "success"
        try:
            if tail is not None and len(tail) > 0:
                tail_text = asr_service.feed(tail, is_final=True)
                if tail_text:
                    text += tail_text
                    self.typer.append(tail_text)
        except Exception as e:
            error = str(e)
            status = "error"
            print(f"流式识别出错: {e}")
            logging.error("流式识别异常", exc_info=True)

        inference_ms = self._stream_inference_ms + int(
            (time.time() - start_time) * 1000
        )
        mem_after_mb = proc.memory_info().rss / 1024 / 1024
        self._stream_text = ""
        self._stream_inference_ms = 0

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

        print(f"停止监听，本次累计 {len(text)} 字" if status == "success" else "识别失败")
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
        self.typer.ensure_focus()
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
        # 先显示托盘图标（蓝色加载中状态），再加载模型
        if self.tray:
            self.tray.start()
            self.tray.set_state("loading")
        print("正在加载模型...")
        logging.info("开始加载模型")
        asr_service.get_model()
        self._set_state("idle")
        logging.info("模型加载完成")
        print("监听中：按 F8 开始/停止持续听写，按 Esc 停止（不冲刷尾部）")

        try:
            with pynput.keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            ) as listener:
                self.listener = listener
                while self._running and listener.is_alive():
                    if self._pending_finalize:
                        self._handle_stream_stop()
                    elif self._pending_audio is not None:
                        self._handle_batch_processing()
                    elif self.is_streaming_model and self.state == "streaming":
                        self._feed_stream_chunk()
                    time.sleep(0.05)
                if self.listener:
                    self.listener.stop()
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
