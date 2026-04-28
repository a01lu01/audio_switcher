# -*- coding: utf-8 -*-
"""测试音频设备切换"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_switcher.switcher import get_switcher


def main():
    print("=" * 50)
    print("音频设备检测")
    print("=" * 50)

    switcher = get_switcher()

    # 列出设备
    switcher.list_devices()

    # 获取当前设备
    current = switcher.get_default_playback_device()
    print(f"当前默认播放设备: {current}")


if __name__ == "__main__":
    main()
