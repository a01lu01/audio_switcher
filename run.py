# -*- coding: utf-8 -*-
"""音频自动切换工具 - 直接启动入口"""
import sys
import os
from pathlib import Path

# 添加项目路径到 sys.path
project_dir = Path(__file__).parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

os.chdir(project_dir)

# 修复导入
from audio_switcher.main_window import MainWindow


def main():
    """主函数"""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    # 启用高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # 设置全局默认字体：Microsoft YaHei UI（Qt 自动 fallback）
    font = QFont("Microsoft YaHei UI")
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # 静默启动：创建主窗口但不显示，只在托盘中运行
    window = MainWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
