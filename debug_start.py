# -*- coding: utf-8 -*-
"""调试启动脚本"""
import sys
import traceback
print("[1] 导入模块...")
try:
    from PySide6.QtWidgets import QApplication
    print("[2] PySide6 导入成功")
except Exception as e:
    print(f"[X] PySide6 导入失败: {e}")
    sys.exit(1)

print("[3] 创建 QApplication...")
app = QApplication(sys.argv)
print("[4] QApplication 创建成功")

print("[5] 测试深色模式检测...")
try:
    import subprocess
    result = subprocess.run([
        'powershell', '-Command',
        "(Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' -Name 'AppsUseLightTheme' -ErrorAction SilentlyContinue).AppsUseLightTheme"
    ], capture_output=True, timeout=5)
    print(f"    深色模式检测结果: {result.stdout.decode('utf-8', errors='ignore').strip()}")
except Exception as e:
    print(f"    深色模式检测失败: {e}")

print("[6] 导入主窗口...")
try:
    from audio_switcher.main_window import MainWindow
    print("[7] MainWindow 导入成功")
except Exception as e:
    print(f"[X] MainWindow 导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[8] 创建 MainWindow...")
try:
    window = MainWindow()
    print("[9] MainWindow 创建成功")
except Exception as e:
    print(f"[X] MainWindow 创建失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[10] 静默启动（托盘模式）...")
print("[11] 进入主循环")
sys.exit(app.exec())
