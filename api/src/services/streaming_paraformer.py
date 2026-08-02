"""流式 Paraformer 识别服务（paraformer-zh-streaming）

按 chunk 增量解码：每次 feed() 返回本段新识别出的文本（非整句全量），
调用方负责把各段文本拼接起来；句尾用 is_final=True 触发缓存冲刷，
再通过 punctuate() 补标点。
"""

import os
import subprocess
import tempfile
import time

import numpy as np
import psutil
import soundfile
import torch
import torchaudio

from funasr import AutoModel

from src.core.config import (
    ASR_PUNC,
    ASR_STREAM_CHUNK_MS,
    DEVICE,
    MODEL_KWARGS,
    STREAMING_PUNC_MODEL_DIR,
)


class StreamingParaformerService:
    """FunASR 流式 Paraformer 服务"""

    def __init__(self, spec=None):
        """spec: asr_registry.ASRSpec，缺省时使用默认模型名"""
        self.name = spec.name if spec else "paraformer-streaming"
        self.model_id = spec.model_id if spec else "paraformer-zh-streaming"
        self.mode = spec.mode if spec else "stream"
        self._model = None
        self._punc_model = None
        self._cache = {}

    @property
    def chunk_size(self):
        """FunASR 流式 chunk 配置：[0, 显示粒度, 前瞻]，单位 60ms"""
        units = max(5, round(ASR_STREAM_CHUNK_MS / 60))
        return [0, units, max(1, units // 2)]

    @property
    def chunk_samples(self):
        """一个 chunk 对应的 16kHz 采样点数（与模型内部 stride 保持一致）"""
        return int(self.chunk_size[1] * 960)

    def get_model(self):
        if self._model is None:
            proc = psutil.Process(os.getpid())
            mem_before = proc.memory_info().rss
            start_time = time.time()

            self._model = AutoModel(
                model=self.model_id,
                device=DEVICE,
                **MODEL_KWARGS,
            )

            duration = time.time() - start_time
            mem_after = proc.memory_info().rss
            delta_mb = (mem_after - mem_before) / 1024 / 1024
            print(
                f"[streaming-paraformer] 模型加载完成 | "
                f"耗时={duration:.2f}s | "
                f"内存={mem_before / 1024 / 1024:.0f}MB→{mem_after / 1024 / 1024:.0f}MB | "
                f"增量={delta_mb:+.0f}MB"
            )
        return self._model

    def reset_stream(self):
        """清空当前说话流式的 cache，开始新一轮识别前调用"""
        self._cache = {}

    def feed(self, audio: np.ndarray, is_final: bool = False, cache=None):
        """增量识别一块音频

        Args:
            audio: 16kHz 单声道 float32 采样点数组
            is_final: 是否为本次说话的最后一个音频块（强制冲刷缓存）
            cache: 默认使用服务实例级 cache（桌面端每轮说话复用）；
                  批量兼容路径可传入独立 dict，避免并发请求互相干扰

        Returns:
            本块新识别出的文本（未补标点），可能为空字符串
        """
        if audio is None or len(audio) == 0:
            return ""
        # 防御：确保是一维 float32 采样点（多声道取平均）
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = np.ascontiguousarray(audio)
        model = self.get_model()
        cache = cache if cache is not None else self._cache
        res = model.generate(
            input=audio,
            cache=cache,
            is_final=is_final,
            chunk_size=self.chunk_size,
            encoder_chunk_look_back=4,
            decoder_chunk_look_back=1,
        )
        return res[0]["text"] or ""

    def punctuate(self, text: str) -> str:
        """给最终文本补标点；ct-punc 不可用时原样返回"""
        text = text or ""
        if not text or not ASR_PUNC:
            return text
        try:
            self._load_punc()
            res = self._punc_model.generate(input=text)
            return res[0]["text"] or text
        except Exception:
            print("[streaming-paraformer] 标点模型不可用，返回原文")
            return text

    def _load_punc(self):
        """懒加载标点模型（进程内只加载一次）"""
        if self._punc_model is None:
            self._punc_model = AutoModel(
                model=STREAMING_PUNC_MODEL_DIR,
                device=DEVICE,
                **MODEL_KWARGS,
            )
        return self._punc_model

    def warmup(self):
        """预加载标点模型，减少停止定稿时的首次加载延迟"""
        if self.mode == "stream" and ASR_PUNC:
            try:
                self._load_punc()
            except Exception:
                print("[streaming-paraformer] 标点模型预加载失败，停止时再试")

    def recognize(self, audio_path: str) -> str:
        """批量兼容：整段音频按 chunk 走流式解码，返回补标点的完整文本"""
        audio = self._load_audio(audio_path)
        if audio is None or len(audio) == 0:
            return ""

        cache = {}
        parts = []
        chunk_samples = self.chunk_samples
        start = 0
        total = len(audio)
        while start < total:
            chunk = audio[start : start + chunk_samples]
            start += chunk_samples
            is_final = start >= total
            text = self.feed(chunk, is_final=is_final, cache=cache)
            if text:
                parts.append(text)
        return self.punctuate("".join(parts))

    @staticmethod
    def _load_audio(audio_path: str):
        """读取任意格式音频，重采样为 16kHz 单声道 float32 numpy 数组

        优先用 soundfile（mp3/wav/flac 等）；失败时用 ffmpeg 转成
        16kHz 单声道 wav 再读取（ffmpeg 为系统依赖，见 README）。
        """
        try:
            audio, sr = soundfile.read(audio_path, dtype="float32")
        except Exception:
            try:
                audio, sr = StreamingParaformerService._ffmpeg_load(audio_path)
            except Exception:
                print(f"[streaming-paraformer] 音频加载失败: {audio_path}")
                return None
        if sr != 16000:
            waveform = torch.from_numpy(audio)
            if waveform.ndim == 1:
                waveform = waveform.unsqueeze(0)
            waveform = torchaudio.functional.resample(waveform, sr, 16000)
            audio = waveform[0].numpy()
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        return np.ascontiguousarray(audio, dtype=np.float32)

    @staticmethod
    def _ffmpeg_load(audio_path: str):
        """用 ffmpeg 把任意音频转成 16kHz 单声道 wav 后读取"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_wav = f.name
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", audio_path,
                    "-ar", "16000", "-ac", "1", "-f", "wav", tmp_wav,
                ],
                check=True,
                capture_output=True,
            )
            return soundfile.read(tmp_wav, dtype="float32")
        finally:
            os.unlink(tmp_wav)
