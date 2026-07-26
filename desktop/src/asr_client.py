"""语音输入客户端主程序"""
import os
import tempfile
import time
import platform

import pynput
import pyperclip
import requests
import scipy.io.wavfile as wavfile
from pynput import keyboard

from src.audio_recorder import AudioRecorder


# API 配置
ASR_API_URL = "http://localhost:8000/api/v1/asr"

# 平台配置
IS_MAC = platform.system() == "Darwin"
PASTE_KEY = keyboard.Key.cmd if IS_MAC else keyboard.Key.ctrl


class ASRClient:
    """语音输入客户端"""

    def __init__(self):
        self.recorder = AudioRecorder()
        self.state = "idle"  # idle -> recording -> processing -> idle
        self.listener = None
        self._trigger_lock = False  # 防止重复触发
        self._running = True  # 运行标志

    def _on_press(self, key):
        """按键按下回调"""
        if key == keyboard.Key.esc:
            self._running = False
            return

        if key == keyboard.Key.f8 and not self._trigger_lock:
            self._trigger_lock = True
            self._toggle_recording()

    def _on_release(self, key):
        """按键释放回调"""
        if key == keyboard.Key.f8:
            self._trigger_lock = False

    def _toggle_recording(self):
        """切换录音状态"""
        if self.state == "idle":
            self._start_recording()
        elif self.state == "recording":
            self._stop_recording()
        elif self.state == "processing":
            pass  # 处理中忽略
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
        print("\u23F9 停止录音，识别中...")
        audio_data = self.recorder.stop()

        # 计算录音时长
        record_duration = time.time() - self._record_start_time
        print(f"\u23F5 录音时长: {record_duration:.2f}秒")

        if len(audio_data) == 0:
            print("\u274C 录音为空")
            self.state = "idle"
            return

        # 保存临时 wav 文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav = f.name

        try:
            wavfile.write(temp_wav, AudioRecorder.SAMPLERATE, audio_data)
            text = self._call_asr_api(temp_wav)
            if text:
                self._paste_to_focus(text)
                print(f"\u2705 {text}")
            else:
                print("\u274C 识别失败")
        finally:
            os.unlink(temp_wav)

        self.state = "idle"

    def _call_asr_api(self, wav_path: str) -> str:
        """调用 ASR API 识别音频"""
        start_time = time.time()
        print(f"\u23F3 发送 API 请求: {ASR_API_URL} | time={time.strftime('%H:%M:%S')}")
        try:
            with open(wav_path, "rb") as f:
                files = {"file": ("audio.wav", f, "audio/wav")}
                response = requests.post(ASR_API_URL, files=files, timeout=30)
            response.raise_for_status()
            result = response.json()

            # 计算 API 请求时长
            api_duration = time.time() - start_time
            print(f"\u23F5 API 识别时长: {api_duration:.2f}秒")

            return result.get("text", "")
        except requests.exceptions.RequestException as e:
            print(f"\u274C API 请求失败: {e}")
            return ""
        except Exception as e:
            print(f"\u274C 识别出错: {e}")
            return ""

    def _paste_to_focus(self, text: str):
        """将文本粘贴到焦点窗口"""
        # 暂存原剪贴板内容
        try:
            original = pyperclip.paste()
        except Exception:
            original = ""

        # 写入识别结果到剪贴板
        pyperclip.copy(text)
        time.sleep(0.1)

        # 模拟 Ctrl+V 粘贴
        kb = pynput.keyboard.Controller()
        time.sleep(0.1)
        kb.press(PASTE_KEY)
        kb.press("v")
        kb.release("v")
        kb.release(PASTE_KEY)

        # 等待粘贴完成后再恢复剪贴板
        time.sleep(0.3)

        # 恢复原剪贴板内容
        try:
            pyperclip.copy(original)
        except Exception:
            pass

    def run(self):
        """启动客户端"""
        print("监听中，按 F8 开始录音，按 Esc 退出")

        with pynput.keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        ) as listener:
            self.listener = listener
            # 等待监听器停止
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
