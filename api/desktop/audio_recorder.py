"""音频录制模块

支持两种模式：
  - 整段录制（start）：帧全部累计到 frames，stop 时一次性返回，供 SenseVoice 使用
  - 流式录制（start_streaming）：帧同时进入队列，主线程用 read_chunk 按块取走，
    供流式 ASR 边录边识别；stop 前的 drain_remaining 收集尚未取走的音频
"""

import queue

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
        self._streaming = False
        self._chunk_queue: queue.Queue = queue.Queue()
        self._chunk_buffer: list[np.ndarray] = []

    def _callback(self, indata, frames, time, status):
        """sounddevice 录音回调，将音频帧追加到列表（流式模式下同时入队）"""
        if status:
            print(f"录音状态: {status}")
        # sounddevice 的 indata 是二维 (帧数, 声道数)，统一展平成一维，
        # 流式模型要求一维采样点数组；整段模式写 wav 也兼容一维
        frame = indata.copy().reshape(-1)
        # 流式模式下不累计整段音频，避免长时间听写内存无限增长
        if not self._streaming:
            self.frames.append(frame)
        if self._streaming:
            self._chunk_queue.put_nowait(frame)

    def start(self):
        """开始整段录音（非流式）"""
        self._reset()
        self._streaming = False
        self._stream = sd.InputStream(
            samplerate=self.SAMPLERATE,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def start_streaming(self):
        """开始流式录音（帧同时入队，供 read_chunk 取块）"""
        self._reset()
        self._streaming = True
        self._stream = sd.InputStream(
            samplerate=self.SAMPLERATE,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def _reset(self):
        """清空所有状态，供新一轮录制使用"""
        self.frames = []
        self._chunk_queue = queue.Queue()
        self._chunk_buffer = []
        self._streaming = False

    def read_chunk(self, chunk_samples: int):
        """取出一整块流式音频（chunk_samples 个采样点），不足则返回 None"""
        while True:
            try:
                self._chunk_buffer.append(self._chunk_queue.get_nowait())
            except queue.Empty:
                break
        if not self._chunk_buffer:
            return None
        total = sum(len(f) for f in self._chunk_buffer)
        if total < chunk_samples:
            return None
        audio = np.concatenate(self._chunk_buffer).reshape(-1)
        self._chunk_buffer = []
        chunk = audio[:chunk_samples]
        rest = audio[chunk_samples:]
        if len(rest):
            self._chunk_buffer.append(rest)
        return chunk

    def drain_remaining(self) -> np.ndarray:
        """收集队列和缓冲中尚未被 read_chunk 取走的音频（供最后一帧 is_final）"""
        while True:
            try:
                self._chunk_buffer.append(self._chunk_queue.get_nowait())
            except queue.Empty:
                break
        if not self._chunk_buffer:
            return np.array([], dtype=self.DTYPE)
        audio = np.concatenate(self._chunk_buffer).reshape(-1)
        self._chunk_buffer = []
        return audio

    def stop(self) -> np.ndarray:
        """停止录音，返回音频数据"""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._streaming = False
        # 合并所有帧
        if self.frames:
            audio_data = np.concatenate(self.frames, axis=0)
        else:
            audio_data = np.array([], dtype=self.DTYPE)
        return audio_data
