"""音频录制模块"""
import numpy as np
import sounddevice as sd


class AudioRecorder:
    """音频录制器，使用 sounddevice 采集麦克风音频"""

    SAMPLERATE = 16000
    CHANNELS = 1
    DTYPE = "float32"

    def __init__(self):
        self.frames: list[np.ndarray] = []
        self._stream = None

    def _callback(self, indata, frames, time, status):
        """sounddevice 录音回调，将音频帧追加到列表"""
        if status:
            print(f"录音状态: {status}")
        self.frames.append(indata.copy())

    def start(self):
        """开始录音"""
        self.frames = []
        self._stream = sd.InputStream(
            samplerate=self.SAMPLERATE,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """停止录音，返回音频数据"""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        # 合并所有帧
        if self.frames:
            audio_data = np.concatenate(self.frames, axis=0)
        else:
            audio_data = np.array([], dtype=self.DTYPE)
        return audio_data
