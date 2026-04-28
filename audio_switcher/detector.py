# -*- coding: utf-8 -*-
"""麦克风活动检测器"""
import time
import threading
from typing import Callable, Optional
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    print("sounddevice 未安装")


class MicDetector:
    """麦克风活动检测器"""

    def __init__(self, config):
        self.config = config
        self.stream = None
        self.is_running = False
        self.thread = None

        # 状态
        self.mic_active = False
        self.silent_count = 0
        self.last_volume = 0.0

        # 回调
        self.on_status_change: Optional[Callable] = None
        self.on_volume_change: Optional[Callable] = None

        # 参数
        self.threshold = config.get('threshold', 0.005)
        self.sample_rate = config.get('sample_rate', 16000)
        self.blocksize = config.get('blocksize', 16000)
        self.silent_count_threshold = config.get('silent_count', 6)

    def _audio_callback(self, indata, frames, time_info, status):
        """音频回调"""
        if status:
            return

        # 计算 RMS 音量
        volume = np.sqrt(np.mean(indata**2))
        self.last_volume = float(volume)

        # 直接用当前音量判断（silent_count 机制已提供防抖延迟）
        has_sound = volume >= self.threshold

        # 状态判断
        old_active = self.mic_active

        if has_sound:
            self.silent_count = 0
            self.mic_active = True
        else:
            self.silent_count += 1
            if self.mic_active and self.silent_count >= self.silent_count_threshold:
                self.mic_active = False

        # 触发回调
        if old_active != self.mic_active:
            if self.on_status_change:
                self.on_status_change(self.mic_active)

        if self.on_volume_change:
            self.on_volume_change(self.last_volume, has_sound)

    def start(self) -> bool:
        """启动检测"""
        if self.is_running:
            return True

        try:
            # 重置状态
            self.mic_active = False
            self.silent_count = 0

            # 更新参数
            self.threshold = self.config.get('threshold', 0.005)
            self.sample_rate = self.config.get('sample_rate', 16000)
            self.blocksize = self.config.get('blocksize', 16000)
            self.silent_count_threshold = self.config.get('silent_count', 6)

            # 启动音频流
            self.stream = sd.InputStream(
                device=None,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.blocksize,
                callback=self._audio_callback,
                dtype='float32'
            )
            self.stream.start()
            self.is_running = True
            return True
        except Exception as e:
            print(f"启动麦克风检测失败: {e}")
            return False

    def stop(self):
        """停止检测"""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None
        self.is_running = False

    def get_devices(self):
        """获取可用输入设备"""
        try:
            devices = sd.query_devices()
            if isinstance(devices, list):
                return [d for d in devices if d['max_input_channels'] > 0]
            elif devices['max_input_channels'] > 0:
                return [devices]
        except:
            pass
        return []

    def update_config(self):
        """更新配置"""
        self.threshold = self.config.get('threshold', 0.005)
        self.sample_rate = self.config.get('sample_rate', 16000)
        self.blocksize = self.config.get('blocksize', 16000)
        self.silent_count_threshold = self.config.get('silent_count', 6)
