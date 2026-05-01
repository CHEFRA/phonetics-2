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


class ASRClient:
    """语音输入客户端"""

    def __init__(self):
        self.recorder = AudioRecorder()
        self.state = "idle"  # idle -> recording -> processing -> idle
        self.listener = None
        self._pressed_keys: set = set()
        self._trigger_lock = False
        self._running = True

    def _on_press(self, key):
        """按键按下回调"""
        if key == keyboard.Key.esc:
            self._running = False
            return

        self._pressed_keys.add(key)
        ctrl = keyboard.Key.ctrl_l in self._pressed_keys or keyboard.Key.ctrl_r in self._pressed_keys
        shift = keyboard.Key.shift_l in self._pressed_keys or keyboard.Key.shift_r in self._pressed_keys
        space = keyboard.Key.space in self._pressed_keys

        if ctrl and shift and space and not self._trigger_lock:
            self._trigger_lock = True
            self._toggle_recording()

    def _on_release(self, key):
        """按键释放回调"""
        self._pressed_keys.discard(key)
        ctrl = keyboard.Key.ctrl_l in self._pressed_keys or keyboard.Key.ctrl_r in self._pressed_keys
        shift = keyboard.Key.shift_l in self._pressed_keys or keyboard.Key.shift_r in self._pressed_keys
        space = keyboard.Key.space in self._pressed_keys
        if not (ctrl or shift or space):
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
        print("\U0001F534 录音中...")

    def _stop_recording(self):
        """停止录音"""
        self.state = "processing"
        print("⏹ 停止录音，识别中...")
        audio_data = self.recorder.stop()

        record_duration = time.time() - self._record_start_time
        print(f"⏵ 录音时长: {record_duration:.2f}秒")

        if len(audio_data) == 0:
            print("❌ 录音为空")
            self.state = "idle"
            return

        # 保存临时 wav 文件（模型需要文件路径输入）
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav = f.name

        try:
            wavfile.write(temp_wav, AudioRecorder.SAMPLERATE, audio_data)
            text = self._recognize(temp_wav)
            if text:
                self._paste_to_focus(text)
                print(f"✅ {text}")
            else:
                print("❌ 识别失败")
        finally:
            os.unlink(temp_wav)

        self.state = "idle"

    def _recognize(self, wav_path: str) -> str:
        """直接调用本地模型识别音频"""
        start_time = time.time()
        print(f"⏳ 调用本地模型 | time={time.strftime('%H:%M:%S')}")
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
        print(f"[debug] _paste_to_focus: text={text!r}, IS_MAC={IS_MAC}, PASTE_KEY={PASTE_KEY!r}, PASTE_KEY type={type(PASTE_KEY)}")
        try:
            original = pyperclip.paste()
            print(f"[debug] 原始剪贴板: {original!r}")
        except Exception as e:
            print(f"[debug] 读取原始剪贴板失败: {e}")
            original = ""

        pyperclip.copy(text)
        time.sleep(0.1)
        after_copy = pyperclip.paste()
        print(f"[debug] 写入后剪贴板: {after_copy!r}")

        kb = pynput.keyboard.Controller()
        print(f"[debug] Controller created: {kb}")
        time.sleep(0.1)

        print(f"[debug] 准备 press PASTE_KEY")
        kb.press(PASTE_KEY)
        print(f"[debug] 已 press PASTE_KEY")
        time.sleep(0.05)
        print(f"[debug] 准备 press v")
        kb.press("v")
        print(f"[debug] 已 press v")
        time.sleep(0.05)
        print(f"[debug] 准备 release v")
        kb.release("v")
        print(f"[debug] 已 release v")
        time.sleep(0.05)
        print(f"[debug] 准备 release PASTE_KEY")
        kb.release(PASTE_KEY)
        print(f"[debug] 已 release PASTE_KEY")

        time.sleep(0.3)

        after_paste = pyperclip.paste()
        print(f"[debug] 粘贴后剪贴板: {after_paste!r}")

        try:
            pyperclip.copy(original)
            print(f"[debug] 已恢复原始剪贴板")
        except Exception as e:
            print(f"[debug] 恢复剪贴板失败: {e}")

    def run(self):
        """启动客户端"""
        print("正在加载模型...")
        sensevoice_service.get_model()
        print("监听中，按 Ctrl+Shift+Space 开始录音，按 Esc 退出")

        with pynput.keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        ) as listener:
            self.listener = listener
            while self._running and listener.is_alive():
                time.sleep(0.1)
            if self.listener:
                self.listener.stop()
        print("已退出")


def main():
    client = ASRClient()
    client.run()


if __name__ == "__main__":
    main()
