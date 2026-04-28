# -*- coding: utf-8 -*-
"""音频自动切换工具 - 主入口"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from audio_switcher.main_window import MainWindow


def main():
    """主函数"""
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
