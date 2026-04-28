# -*- coding: utf-8 -*-
"""测试 PySide6 导入"""
import sys
sys.path.insert(0, r'c:\Users\Why\Downloads\音频自动切换工具')
try:
    from audio_switcher.main_window import MainWindow
    print("OK: MainWindow imported successfully")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
