# -*- coding: utf-8 -*-
"""系统托盘管理器"""
from pathlib import Path
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item
from PySide6.QtCore import QObject, Signal


class _TraySignals(QObject):
    """信号中继：pystray 线程 → Qt 主线程

    pystray 的回调运行在自己的线程里，没有 Qt 事件循环，
    QTimer.singleShot 从该线程调用时回调不会被执行。
    用 Qt Signal 则是线程安全的，自动走 QueuedConnection 回主线程。
    """
    show_requested = Signal()
    quit_requested = Signal()
    switch_requested = Signal(str)
    toggle_requested = Signal()


class TrayManager:
    """系统托盘管理器"""

    def __init__(self, on_show, on_quit, on_switch, on_toggle):
        self.on_show = on_show
        self.on_quit = on_quit
        self.on_switch = on_switch
        self.on_toggle = on_toggle
        self.icon = None
        self.is_running = False

        # 信号中继：所有 pystray 回调通过信号发到 Qt 主线程
        self.signals = _TraySignals()
        self.signals.show_requested.connect(on_show)
        self.signals.quit_requested.connect(on_quit)
        self.signals.switch_requested.connect(on_switch)
        self.signals.toggle_requested.connect(on_toggle)

    def _create_icon_image(self) -> Image:
        """创建托盘图标 - 使用专用小尺寸绘制确保清晰"""
        from audio_switcher.main_window import is_dark_mode
        bg_color = (0x0f, 0x0f, 0x12) if is_dark_mode() else (0xf7, 0xf8, 0xf8)
        GREEN = (0x22, 0xC5, 0x5E)

        # 用 32x32 绘制（托盘小图标的标准尺寸，缩放损失最小）
        size = 32
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        s = size / 256
        cx = size // 2

        # 32x32 专用绘制：头带 + 耳罩 + 耳垫
        band_r = int(75 * s)
        band_w = max(int(16 * s), 2)
        draw.arc([cx - band_r, int(45*s), cx + band_r, int(215*s)],
                 start=180, end=0, fill=GREEN, width=band_w)
        ear_w = int(48 * s)
        ear_h = int(62 * s)
        ear_y = int(118 * s)
        pad = int(5 * s)
        lx = cx - band_r - int(2*s)
        rx = cx + band_r - ear_w + int(2*s)
        DARK_GREEN = (0x1A, 0x9E, 0x4A)
        draw.rounded_rectangle([lx, ear_y, lx + ear_w, ear_y + ear_h],
                               radius=max(int(10*s), 1), fill=GREEN)
        draw.rounded_rectangle([lx+pad, ear_y+pad, lx+ear_w-pad, ear_y+ear_h-pad],
                               radius=max(int(6*s), 1), fill=DARK_GREEN)
        draw.rounded_rectangle([rx, ear_y, rx + ear_w, ear_y + ear_h],
                               radius=max(int(10*s), 1), fill=GREEN)
        draw.rounded_rectangle([rx+pad, ear_y+pad, rx+ear_w-pad, ear_y+ear_h-pad],
                               radius=max(int(6*s), 1), fill=DARK_GREEN)

        # 合成到背景上（pystray Windows 需要不透明 RGB）
        background = Image.new("RGBA", (size, size), (*bg_color, 255))
        background.paste(img, (0, 0), img)
        return background.convert("RGB")

    def create_menu(self):
        """创建右键菜单"""
        status_text = "运行中" if self.is_running else "已停止"

        return pystray.Menu(
            Item("🎧 音频自动切换工具", self._do_nothing, enabled=False),
            pystray.Menu.SEPARATOR,
            Item(f"状态: {status_text}", self._do_nothing, enabled=False),
            Item("切换到耳机", lambda: self.signals.switch_requested.emit("headphone")),
            Item("切换到扬声器", lambda: self.signals.switch_requested.emit("speaker")),
            pystray.Menu.SEPARATOR,
            Item("开始/停止监听", lambda: self.signals.toggle_requested.emit()),
            Item("显示主窗口", lambda: self.signals.show_requested.emit()),
            pystray.Menu.SEPARATOR,
            Item("退出", lambda: self.signals.quit_requested.emit()),
        )

    def _do_nothing(self):
        """空操作"""
        pass

    def update_status(self, is_running: bool):
        """更新运行状态"""
        self.is_running = is_running
        self.update_menu()

    def update_menu(self):
        """更新菜单"""
        if self.icon:
            self.icon.menu = self.create_menu()

    def set_icon(self, icon_type: str = "normal"):
        """设置图标状态"""
        if self.icon:
            self.icon.icon = self._create_icon_image()

    def show(self):
        """显示托盘图标"""
        if self.icon is not None:
            return  # 已经在运行，不重复启动
        self.icon = pystray.Icon(
            "audio_switcher",
            self._create_icon_image(),
            "音频自动切换工具",
            menu=self.create_menu()
        )
        # 左键点击事件 → 通过信号中继到 Qt 主线程
        self.icon.on_activate = lambda icon, item: self.signals.show_requested.emit()
        self.icon.run_detached()

    def hide(self):
        """隐藏托盘图标"""
        if self.icon:
            self.icon.stop()
            self.icon = None

    def notify(self, title: str, message: str):
        """显示通知"""
        if self.icon:
            self.icon.notify(message, title)
