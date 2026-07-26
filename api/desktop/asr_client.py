"""语音输入客户端主程序（直接调用本地模型）"""

import os
import tempfile
import time
import platform

import pynput
import pyperclip
import scipy.io.wavfile as wavfile
from pynput import keyboard

from audio_recorder import AudioRecorder
from src.services.sensevoice import sensevoice_service

# 平台配置
IS_MAC = platform.system() == "Darwin"
PASTE_KEY = keyboard.Key.cmd if IS_MAC else keyboard.Key.ctrl
PASTE_DELAY = 0.618  # 粘贴前等待时间（秒），用于避开热键释放

# 热键配置（修改此处即可更改快捷键）
# 单键：{keyboard.Key.f8}
# 组合键：{keyboard.Key.ctrl_l, keyboard.Key.shift_l, keyboard.Key.space}
HOTKEY_KEYS = {keyboard.Key.f8}


class ASRClient:
    """语音输入客户端"""

    def __init__(self):
        self.recorder = AudioRecorder()
        self.state = "idle"  # idle -> recording -> processing -> idle
        self.listener = None
        self._pressed_keys: set = set()
        self._trigger_lock = False
        self._running = True
        self._pending_audio = None

    def _on_press(self, key):
        """按键按下回调"""
        if key == keyboard.Key.esc:
            self._running = False
            return

        self._pressed_keys.add(key)
        if HOTKEY_KEYS.issubset(self._pressed_keys) and not self._trigger_lock:
            self._trigger_lock = True
            self._toggle_recording()

    def _on_release(self, key):
        """按键释放回调"""
        self._pressed_keys.discard(key)
        if not HOTKEY_KEYS.intersection(self._pressed_keys):
            self._trigger_lock = False

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
        self.state = "recording"
        self._record_start_time = time.time()
        self.recorder.start()
        print("\U0001f534 录音中...")

    def _stop_recording(self):
        """停止录音"""
        print("⏹ 停止录音")
        audio_data = self.recorder.stop()

        record_duration = time.time() - self._record_start_time
        print(f"⏵ 录音时长: {record_duration:.2f}秒")

        if len(audio_data) == 0:
            print("❌ 录音为空")
            return

        self._pending_audio = audio_data

    def _recognize(self, wav_path: str) -> str:
        """直接调用本地模型识别音频"""
        start_time = time.time()
        # print(f"⏳ 调用本地模型 | time={time.strftime('%H:%M:%S')}")
        try:
            text = sensevoice_service.recognize(wav_path)

            api_duration = time.time() - start_time
            print(f"⏵ 识别时长: {api_duration:.2f}秒")

            return text
        except Exception as e:
            print(f"❌ 识别出错: {e}")
            return ""

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
        print("正在加载模型...")
        sensevoice_service.get_model()
        print("监听中，按 F8 开始录音，按 Esc 退出")

        try:
            with pynput.keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            ) as listener:
                self.listener = listener
                while self._running and listener.is_alive():
                    if self._pending_audio is not None:
                        audio_data = self._pending_audio
                        self._pending_audio = None
                        self.state = "processing"

                        # 保存临时 wav 文件（模型需要文件路径输入）
                        with tempfile.NamedTemporaryFile(
                            suffix=".wav", delete=False
                        ) as f:
                            temp_wav = f.name

                        try:
                            wavfile.write(
                                temp_wav, AudioRecorder.SAMPLERATE, audio_data
                            )
                            text = self._recognize(temp_wav)
                            if text:
                                time.sleep(PASTE_DELAY)  # 避开热键释放
                                self._paste_to_focus(text)
                                print(f"✅ {text}")
                            else:
                                print("❌ 识别失败")
                        finally:
                            os.unlink(temp_wav)

                        self.state = "idle"
                    time.sleep(0.1)
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
