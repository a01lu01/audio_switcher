# -*- coding: utf-8 -*-
"""配置管理"""
import json
import os
from pathlib import Path


class Config:
    """配置管理器"""

    DEFAULT_CONFIG = {
        # 音频检测参数
        "threshold": 0.005,
        "sample_rate": 16000,
        "blocksize": 16000,
        "silent_count": 6,

        # 设备名称
        "headphone_name": "扬声器 (AKG N9 Hybrid)",
        "speaker_name": "扬声器 (EDIFIER N300)",

        # 功能开关
        "auto_switch": True,
        "show_notifications": True,
        "start_minimized": False,
        "auto_start": False,

        # 快捷键 (格式: "ctrl+shift+1")
        "hotkey_switch": "ctrl+shift+h",
        "hotkey_toggle": "ctrl+shift+t",
    }

    def __init__(self):
        self.config_dir = Path.home() / ".audio_switcher"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.data = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception:
                pass

    def save(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"配置保存失败: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def reset(self):
        """重置为默认配置"""
        self.data = self.DEFAULT_CONFIG.copy()
        self.save()
