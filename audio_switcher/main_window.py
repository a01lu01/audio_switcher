# -*- coding: utf-8 -*-
"""Windows 11 风格主窗口"""
import sys
import subprocess
from pathlib import Path

# 尝试导入 PySide6
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QFrame, QSlider, QGroupBox, QCheckBox,
        QLineEdit, QScrollArea, QSizePolicy, QGraphicsOpacityEffect,
        QComboBox, QTextEdit, QStackedWidget
    )
    from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QSize, QParallelAnimationGroup, QEvent
    from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient, QIcon, QAction, QPixmap
    from PySide6.QtSvg import QSvgRenderer
except ImportError as e:
    print(f"PySide6 导入失败: {e}")
    print("请运行: pip install PySide6")
    raise  # 重新抛出，让错误信息完整显示

from audio_switcher.config import Config
from audio_switcher.detector import MicDetector
from audio_switcher.switcher import get_switcher
from audio_switcher.hotkey import HotkeyManager
from audio_switcher.tray import TrayManager
import re


# ============================================================
# SVG 图标工具
# ============================================================
# SVG 图标路径（相对于项目根目录）
_ICON_DIR = Path(__file__).parent.parent / "icon"

# 图标映射：名称 -> 文件名
_ICON_FILES = {
    "headphone":   "24gf-headphones.svg",
    "pause":       "暂停-outline.svg",
    "mute":        "声音静音.svg",
    "sound":       "声音开.svg",
    "play":        "开始-outline.svg",
    "stop":        "停止-outline.svg",
    "refresh":     "刷新.svg",
    "save":        "保存.svg",
    "check":       "控件.svg",      # 保存成功 ✓
    "settings":    "icon_设置.svg",
    "log":         "使用文档.svg",
}

# 缓存：缓存已渲染的 pixmap，避免重复加载
_icon_cache = {}


def _clear_icon_cache():
    """清除图标缓存（主题切换时调用）"""
    global _icon_cache
    _icon_cache.clear()


def _load_svg(name: str, color: str, size: int) -> QPixmap:
    """加载 SVG 图标，替换颜色并渲染为 pixmap"""
    # 先解析语义色名
    resolved_color = WIN11_COLORS.get(color, color)
    # 缓存 key 用解析后的 hex 值，确保主题切换后缓存失效
    cache_key = f"{name}:{resolved_color}:{size}"
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    filepath = _ICON_DIR / _ICON_FILES[name]
    if not filepath.exists():
        return QPixmap()

    svg_content = filepath.read_text(encoding="utf-8")

    # ① 替换已有的 fill 属性
    def replace_fill(m):
        return f'fill="{resolved_color}"'
    svg_colored = re.sub(r'fill="[^"]*"', replace_fill, svg_content)

    # ② 为没有 fill 属性的 path/d 元素注入 fill
    # 将 <path d="..."> 或 <path d='...'> 替换为带 fill 的版本
    def add_fill_to_path(m):
        tag_content = m.group(1)
        # 如果该元素已经有 fill 属性，跳过（上面已处理）
        if 'fill=' in tag_content:
            return m.group(0)
        return f'<path fill="{resolved_color}" {tag_content}>'

    svg_colored = re.sub(r'<path\s+([^>]+)>', add_fill_to_path, svg_colored)

    renderer = QSvgRenderer(svg_colored.encode("utf-8"))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    _icon_cache[cache_key] = pixmap
    return pixmap


def svg_icon(name: str, color: str, size: int) -> QPixmap:
    """返回指定颜色和大小的 SVG pixmap"""
    return _load_svg(name, color, size)


def set_svg_on_label(label: QLabel, name: str, color: str, size: int):
    """将 SVG 图标设置到 QLabel"""
    pixmap = svg_icon(name, color, size)
    if not pixmap.isNull():
        label.setPixmap(pixmap)
        label.setFixedSize(size, size)


def set_svg_on_button(btn: QPushButton, name: str, color: str, size: int, text: str = ""):
    """将 SVG 图标设置到 QPushButton（作为图标 + 文字）"""
    pixmap = svg_icon(name, color, size)
    if not pixmap.isNull():
        btn.setIcon(QIcon(pixmap))
        btn.setIconSize(QSize(size, size))
    if text:
        btn.setText(text)
        # 左图右文模式：图标在左，文字在右
        btn.setLayoutDirection(Qt.LayoutDirection.LeftToRight)


# Windows 11 亮色配色 (Linear Light)
WIN11_LIGHT = {
    'bg_primary': '#FFFFFF',
    'bg_secondary': '#f7f8f8',
    'bg_tertiary': '#f5f5f7',
    'accent': '#5e6ad2',
    'accent_light': '#e8e9f0',
    'text_primary': '#1a1a1f',
    'text_secondary': '#6b6b78',
    'text_tertiary': '#9d9da6',
    'border': '#e8e8ed',
    'success': '#22c55e',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'card_bg': '#FFFFFF',
    # 图标专用语义色
    'icon_default': '#6b6b78',   # 默认图标色 = 次要文字
    'icon_primary': '#1a1a1f',   # 主色图标 = 主文字
}

# Windows 11 暗色配色 (Linear Dark)
WIN11_DARK = {
    'bg_primary': '#0f0f12',
    'bg_secondary': '#1a1a1f',
    'bg_tertiary': '#2a2a30',
    'accent': '#7170ff',
    'accent_light': '#3d3d5c',
    'text_primary': '#f7f8f8',
    'text_secondary': '#d0d6e0',
    'text_tertiary': '#8a8f98',
    'border': '#34343a',
    'success': '#22c55e',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'card_bg': '#191a1b',
    # 图标专用语义色
    'icon_default': '#8a8f98',   # 默认图标色 = 次要文字
    'icon_primary': '#f7f8f8',   # 主色图标 = 主文字
}


def is_dark_mode() -> bool:
    """检测 Windows 是否为深色模式（直接读注册表，不弹 PowerShell 窗口）"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
        )
        value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
        winreg.CloseKey(key)
        # 0 = 深色模式, 1 = 亮色模式
        return value == 0
    except:
        return False


def get_color(key: str) -> str:
    """获取当前主题的颜色"""
    global WIN11_COLORS
    return WIN11_COLORS.get(key, WIN11_LIGHT.get(key, '#FFFFFF'))


# 全局字体设置函数（统一管理）
def app_font(size: int = 10, weight: int = QFont.Normal) -> QFont:
    """创建统一字体：Microsoft YaHei UI，Qt 会自动 fallback"""
    font = QFont("Microsoft YaHei UI", size, weight)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    return font


def update_theme(is_dark: bool):
    """更新全局主题"""
    global WIN11_COLORS
    WIN11_COLORS = WIN11_DARK if is_dark else WIN11_LIGHT
    _clear_icon_cache()  # 主题切换时清除图标缓存
    return WIN11_COLORS


# 当前配色（初始化）
WIN11_COLORS = WIN11_LIGHT.copy()


class Win11Card(QFrame):
    """Windows 11 风格卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Win11Card")

    def _apply_theme(self):
        """应用主题样式"""
        c = WIN11_COLORS
        self.setStyleSheet(f"""
            #Win11Card {{
                background-color: {c['card_bg']};
                border-radius: 8px;
                border: 1px solid {c['border']};
            }}
        """)

    def apply_theme(self):
        """供外部调用的主题更新方法"""
        self._apply_theme()


class StatusCard(Win11Card):
    """状态卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # 状态图标和文字
        self.status_layout = QHBoxLayout()
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(32, 32)
        self.status_text = QLabel("等待启动...")
        self.status_text.setFont(app_font(18, QFont.Weight.Medium))
        self.status_text.setStyleSheet(f"color: {WIN11_COLORS['text_secondary']}")

        self.status_layout.addWidget(self.status_icon)
        self.status_layout.addWidget(self.status_text)
        self.status_layout.addStretch()

        layout.addLayout(self.status_layout)

        # 音量条
        self.volume_layout = QHBoxLayout()
        self.volume_label = QLabel("音量:")
        self.volume_label.setFont(app_font(12))
        self.volume_label.setStyleSheet(f"color: {WIN11_COLORS['text_tertiary']}")

        self.volume_bar = VolumeBar()
        self.volume_value = QLabel("0.000000")
        self.volume_value.setFont(QFont("Consolas", 11))
        self.volume_value.setStyleSheet(f"color: {WIN11_COLORS['text_tertiary']}")
        self.volume_value.setFixedWidth(90)
        self.volume_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.volume_layout.addWidget(self.volume_label)
        self.volume_layout.addWidget(self.volume_bar, 1)
        self.volume_layout.addWidget(self.volume_value)

        layout.addLayout(self.volume_layout)

        # 设备信息
        self.device_layout = QHBoxLayout()
        self.device_label = QLabel("当前设备: 未检测")
        self.device_label.setFont(app_font(11))
        self.device_label.setStyleSheet(f"color: {WIN11_COLORS['text_tertiary']}")
        self.device_layout.addWidget(self.device_label)
        self.device_layout.addStretch()

        layout.addLayout(self.device_layout)

        # 跟踪当前图标名称（用于主题刷新）
        self._current_icon = "pause"

    def update_status(self, is_active: bool, is_running: bool = False):
        """更新状态"""
        if not is_running:
            self._current_icon = "pause"
            self._update_status_icon()
            self.status_text.setText("已停止")
            self.status_text.setStyleSheet(f"color: {WIN11_COLORS['text_tertiary']}")
        elif is_active:
            self._current_icon = "headphone"
            self._update_status_icon()
            self.status_text.setText("麦克风活跃 - 耳机模式")
            self.status_text.setStyleSheet(f"color: {WIN11_COLORS['success']}")
        else:
            self._current_icon = "mute"
            self._update_status_icon()
            self.status_text.setText("麦克风静音 - 扬声器模式")
            self.status_text.setStyleSheet(f"color: {WIN11_COLORS['accent']}")

    def _update_status_icon(self):
        """根据状态更新图标颜色"""
        color = 'text_tertiary'
        if self._current_icon == "headphone":
            color = 'success'
        elif self._current_icon == "mute":
            color = 'accent'
        set_svg_on_label(self.status_icon, self._current_icon, color, 32)

    def update_volume(self, volume: float, threshold: float):
        """更新音量"""
        self.volume_bar.setValue(volume, threshold)
        self.volume_value.setText(f"{volume:.6f}")

    def apply_theme(self):
        """应用主题"""
        c = WIN11_COLORS
        self.setStyleSheet(f"""
            #Win11Card {{
                background-color: {c['card_bg']};
                border-radius: 8px;
                border: 1px solid {c['border']};
            }}
        """)
        self.status_text.setStyleSheet(f"color: {c['text_secondary']}")
        self.volume_label.setStyleSheet(f"color: {c['text_tertiary']}")
        self.volume_value.setStyleSheet(f"color: {c['text_tertiary']}")
        self.device_label.setStyleSheet(f"color: {c['text_tertiary']}")
        # 刷新图标颜色（不改变状态文字）
        self._update_status_icon()


class VolumeBar(QFrame):
    """音量条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.volume = 0.0
        self.threshold = 0.005
        self.setMinimumHeight(8)
        self.setMaximumHeight(8)
        self.setStyleSheet("background: transparent;")

    def setValue(self, volume: float, threshold: float):
        self.volume = volume
        self.threshold = threshold
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(WIN11_COLORS['border']))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)

        # 音量
        max_width = int(self.width() * min(self.volume / (self.threshold * 20), 1.0))
        if max_width > 0:
            if self.volume >= self.threshold:
                painter.setBrush(QColor(WIN11_COLORS['success']))
            else:
                painter.setBrush(QColor(WIN11_COLORS['accent']))
            painter.drawRoundedRect(0, 0, max_width, self.height(), 4, 4)

        # 阈值线
        threshold_x = int(self.width() * min(self.threshold / (self.threshold * 20), 1.0))
        painter.setPen(QPen(QColor(WIN11_COLORS['warning']), 2))
        painter.drawLine(threshold_x, 0, threshold_x, self.height())


class ControlPanel(Win11Card):
    """控制面板 - 开始/停止监听"""

    switch_clicked = Signal(str)  # "headphone" or "speaker"
    toggle_clicked = Signal()  # 开始/停止监听

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 标题
        title = QLabel("快速控制")
        title.setFont(app_font(13, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {WIN11_COLORS['text_primary']}")
        layout.addWidget(title)

        # 按钮组
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_headphone = QPushButton()
        self.btn_headphone.setFont(app_font(11))
        self.btn_headphone.setCursor(Qt.PointingHandCursor)
        self.btn_headphone.clicked.connect(lambda: self.switch_clicked.emit("headphone"))
        self._set_btn_icon(self.btn_headphone, "headphone", "切换到耳机")

        self.btn_speaker = QPushButton()
        self.btn_speaker.setFont(app_font(11))
        self.btn_speaker.setCursor(Qt.PointingHandCursor)
        self.btn_speaker.clicked.connect(lambda: self.switch_clicked.emit("speaker"))
        self._set_btn_icon(self.btn_speaker, "sound", "切换到扬声器")

        for btn in [self.btn_headphone, self.btn_speaker]:
            btn.setMinimumHeight(40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {WIN11_COLORS['bg_secondary']};
                    border: 1px solid {WIN11_COLORS['border']};
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: {WIN11_COLORS['text_primary']};
                }}
                QPushButton:hover {{
                    background-color: {WIN11_COLORS['accent_light']};
                    border-color: {WIN11_COLORS['accent']};
                }}
                QPushButton:pressed {{
                    background-color: {WIN11_COLORS['accent']};
                    color: {WIN11_COLORS['bg_primary']};
                }}
            """)

        btn_layout.addWidget(self.btn_headphone)
        btn_layout.addWidget(self.btn_speaker)
        layout.addLayout(btn_layout)

        # 开始/停止按钮
        self.btn_toggle = QPushButton()
        self.btn_toggle.setFont(app_font(13, QFont.Weight.Medium))
        self.btn_toggle.setMinimumHeight(48)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        from functools import partial
        self.btn_toggle.clicked.connect(partial(self.toggle_clicked.emit))
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {WIN11_COLORS['success']};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                color: {WIN11_COLORS['bg_primary']};
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        layout.addWidget(self.btn_toggle)
        self._set_toggle_btn_icon(False)  # False = 播放状态

    def _set_btn_icon(self, btn: QPushButton, icon_name: str, text: str):
        """设置按钮 SVG 图标 + 文字"""
        color = 'icon_primary'
        pixmap = svg_icon(icon_name, color, 20)
        if not pixmap.isNull():
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(QSize(20, 20))
        btn.setText(text)

    def _set_toggle_btn_icon(self, is_playing: bool):
        """设置开始/停止按钮图标"""
        icon_name = "stop" if is_playing else "play"
        text = "停止监听" if is_playing else "开始监听"
        color = '#000000'  # 黑色
        pixmap = svg_icon(icon_name, color, 22)
        if not pixmap.isNull():
            self.btn_toggle.setIcon(QIcon(pixmap))
            self.btn_toggle.setIconSize(QSize(22, 22))
        self.btn_toggle.setText(text)

    def _refresh_btn_icons(self):
        """刷新所有按钮图标（主题切换时调用）"""
        self._set_btn_icon(self.btn_headphone, "headphone", "切换到耳机")
        self._set_btn_icon(self.btn_speaker, "sound", "切换到扬声器")
        self._set_toggle_btn_icon(self.is_running)

    def set_running(self, running: bool):
        """设置运行状态"""
        self.is_running = running
        self._set_toggle_btn_icon(running)
        if running:
            self.btn_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {WIN11_COLORS['error']};
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    color: {WIN11_COLORS['bg_primary']};
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """)
        else:
            self.btn_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {WIN11_COLORS['success']};
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    color: {WIN11_COLORS['bg_primary']};
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """)

    def apply_theme(self):
        """应用主题"""
        c = WIN11_COLORS
        self.setStyleSheet(f"""
            #Win11Card {{
                background-color: {c['card_bg']};
                border-radius: 8px;
                border: 1px solid {c['border']};
            }}
        """)
        self.btn_headphone.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_secondary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 8px 16px;
                color: {c['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {c['accent_light']};
                border-color: {c['accent']};
            }}
        """)
        self.btn_speaker.setStyleSheet(self.btn_headphone.styleSheet())
        # 刷新按钮图标颜色
        self._refresh_btn_icons()
        self.set_running(self.is_running)


class SettingsPanel(Win11Card):
    """设置面板"""

    settings_changed = Signal(dict)

    def __init__(self, config: Config, switcher, parent=None):
        super().__init__(parent)
        self.config = config
        self.switcher = switcher
        # 保存所有需要主题刷新的子控件引用
        self._input_widgets = []   # QLineEdit 列表
        self._combo_widgets = []   # QComboBox 列表
        self._group_widgets = []   # QGroupBox 列表
        self.init_ui()

    def init_ui(self):
        # 强制设置最小高度和 sizePolicy 防止被挤压
        self.setMinimumSize(0, 320)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # 音频检测设置
        group = QGroupBox()
        group.setFont(app_font(11, QFont.Weight.Medium))
        group.setMinimumHeight(80)
        group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {WIN11_COLORS['border']};
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 6px;
                padding-bottom: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                color: {WIN11_COLORS['text_primary']};
            }}
        """)
        self._group_widgets.append(group)

        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)

        # 阈值
        row = self._create_row("音量阈值:", "threshold", "0~1，值越小越灵敏")
        group_layout.addLayout(row)

        # 判定时间
        row = self._create_row("静音判定(秒):", "silent_count", "持续静音多少秒后判定关机")
        group_layout.addLayout(row)

        layout.addWidget(group)

        # 设备设置
        group2 = QGroupBox()
        group2.setFont(app_font(11, QFont.Weight.Medium))
        group2.setMinimumHeight(120)
        group2.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        group2.setStyleSheet(group.styleSheet())
        self._group_widgets.append(group2)

        group_layout2 = QVBoxLayout(group2)
        group_layout2.setSpacing(8)

        # 耳机设备下拉框
        row = self._create_combo_row("耳机设备:", "headphone")
        group_layout2.addLayout(row)

        # 扬声器设备下拉框
        row = self._create_combo_row("扬声器设备:", "speaker")
        group_layout2.addLayout(row)

        # 刷新设备按钮
        btn_refresh = QPushButton()
        btn_refresh.setFont(app_font(10))
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_devices)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {WIN11_COLORS['accent']};
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        self._set_refresh_icon(btn_refresh)
        group_layout2.addWidget(btn_refresh)
        self.btn_refresh = btn_refresh

        layout.addWidget(group2)

        # 快捷键设置
        group3 = QGroupBox()
        group3.setFont(app_font(11, QFont.Weight.Medium))
        group3.setMinimumHeight(60)
        group3.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        group3.setStyleSheet(group.styleSheet())
        self._group_widgets.append(group3)

        group_layout3 = QVBoxLayout(group3)
        group_layout3.setSpacing(8)

        row = self._create_row("切换快捷键:", "hotkey_switch", "如: ctrl+shift+h")
        group_layout3.addLayout(row)

        layout.addWidget(group3)

        # 保存按钮
        self.btn_save = QPushButton()
        self.btn_save.setFont(app_font(11))
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._save)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {WIN11_COLORS['accent']};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: {WIN11_COLORS['bg_primary']};
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        self._set_save_icon(False)
        layout.addWidget(self.btn_save)

        # 初始化设备列表
        self.refresh_devices()
        self.load_config_values()

    def _create_row(self, label: str, key: str, hint: str) -> QHBoxLayout:
        """创建设置行"""
        row = QHBoxLayout()
        row.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFont(app_font(11))
        lbl.setMinimumWidth(100)
        lbl.setStyleSheet(f"color: {WIN11_COLORS['text_primary']}; background: transparent;")
        row.addWidget(lbl)

        edit = QLineEdit()
        edit.setObjectName(key)
        edit.setText(str(self.config.get(key, '')))
        edit.setFont(app_font(11))
        edit.setFixedHeight(32)
        edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        edit.setPlaceholderText(hint)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {WIN11_COLORS['bg_primary']};
                border: 1px solid {WIN11_COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
                color: {WIN11_COLORS['text_primary']};
                min-height: 32px;
            }}
            QLineEdit:focus {{
                border-color: {WIN11_COLORS['accent']};
            }}
        """)
        self._input_widgets.append(edit)
        row.addWidget(edit, 1)

        return row

    def _create_combo_row(self, label: str, key: str) -> QHBoxLayout:
        """创建下拉框行"""
        row = QHBoxLayout()
        row.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFont(app_font(11))
        lbl.setMinimumWidth(100)
        lbl.setStyleSheet(f"color: {WIN11_COLORS['text_primary']}; background: transparent;")
        row.addWidget(lbl)

        combo = QComboBox()
        combo.setFont(app_font(11))
        combo.setFixedHeight(34)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {WIN11_COLORS['bg_primary']};
                border: 1px solid {WIN11_COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
                color: {WIN11_COLORS['text_primary']};
                min-height: 34px;
            }}
            QComboBox:hover {{
                border-color: {WIN11_COLORS['accent']};
            }}
            QComboBox:focus {{
                border-color: {WIN11_COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {WIN11_COLORS['text_secondary']};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {WIN11_COLORS['bg_primary']};
                border: 1px solid {WIN11_COLORS['border']};
                color: {WIN11_COLORS['text_primary']};
                selection-background-color: {WIN11_COLORS['accent']};
            }}
        """)
        self._combo_widgets.append(combo)
        row.addWidget(combo, 1)

        # 保存引用
        if key == "headphone":
            self.combo_headphone = combo
        else:
            self.combo_speaker = combo

        return row

    def refresh_devices(self):
        """刷新设备列表"""
        devices = self.switcher.get_playback_devices()
        print(f"[refresh_devices] found {len(devices)} devices: {[d['name'] for d in devices]}")

        self.combo_headphone.clear()
        self.combo_speaker.clear()

        current_headphone = self.config.get('headphone_name', '')
        current_speaker = self.config.get('speaker_name', '')
        print(f"[refresh_devices] config: headphone={current_headphone!r}, speaker={current_speaker!r}")

        for dev in devices:
            self.combo_headphone.addItem(dev['name'])
            self.combo_speaker.addItem(dev['name'])

        # 全部添加完后再设置当前选中项
        idx_h = self.combo_headphone.findText(current_headphone)
        if idx_h >= 0:
            self.combo_headphone.setCurrentIndex(idx_h)
        else:
            print(f"[refresh_devices] headphone '{current_headphone}' not found, default to 0")
            idx_h = 0
            self.combo_headphone.setCurrentIndex(idx_h)
        print(f"[refresh_devices] headphone idx={idx_h}: {self.combo_headphone.currentText()!r}")

        idx_s = self.combo_speaker.findText(current_speaker)
        if idx_s >= 0:
            self.combo_speaker.setCurrentIndex(idx_s)
        else:
            print(f"[refresh_devices] speaker '{current_speaker}' not found, default to 1")
            idx_s = 1 if self.combo_speaker.count() > 1 else 0
            self.combo_speaker.setCurrentIndex(idx_s)
        print(f"[refresh_devices] speaker idx={idx_s}: {self.combo_speaker.currentText()!r}")

        # 强制重绘，确保选中项在窗口显示前就已渲染
        self.combo_headphone.update()
        self.combo_speaker.update()

    def load_config_values(self):
        """加载配置值到控件"""
        for edit in self.findChildren(QLineEdit):
            key = edit.objectName()
            value = self.config.get(key, '')
            edit.setText(str(value))

    def _on_check_changed(self):
        """复选框状态改变"""
        self.config.set('show_notifications', self.cb_notifications.isChecked())
        self.config.set('auto_start', self.cb_auto_start.isChecked())

    def _set_refresh_icon(self, btn: QPushButton):
        """设置刷新按钮图标"""
        color = 'accent'
        pixmap = svg_icon("refresh", color, 16)
        if not pixmap.isNull():
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(QSize(16, 16))
        btn.setText("刷新设备列表")

    def _set_save_icon(self, is_check: bool):
        """设置保存按钮图标：is_check=True 显示勾，False 显示保存"""
        icon_name = "check" if is_check else "save"
        color = '#FFFFFF'  # 白色
        text = "已保存!" if is_check else "保存设置"
        pixmap = svg_icon(icon_name, color, 18)
        if not pixmap.isNull():
            self.btn_save.setIcon(QIcon(pixmap))
            self.btn_save.setIconSize(QSize(18, 18))
        self.btn_save.setText(text)

    def _save(self):
        """保存设置"""
        # 收集所有输入值
        for edit in self.findChildren(QLineEdit):
            key = edit.objectName()
            value = edit.text()

            # 尝试转换为数字
            try:
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                pass

            self.config.set(key, value)

        # 保存下拉框选择的设备
        self.config.set('headphone_name', self.combo_headphone.currentText())
        self.config.set('speaker_name', self.combo_speaker.currentText())

        self.config.save()
        self.settings_changed.emit(self.config.data)

        # 显示保存成功
        self._set_save_icon(True)
        QTimer.singleShot(1500, lambda: self._set_save_icon(False))

    def apply_theme(self):
        """应用主题"""
        c = WIN11_COLORS
        self.setStyleSheet(f"""
            #Win11Card {{
                background-color: {c['card_bg']};
                border-radius: 8px;
                border: 1px solid {c['border']};
            }}
        """)
        # 刷新所有 QGroupBox 样式
        for grp in self._group_widgets:
            grp.setStyleSheet(f"""
                QGroupBox {{
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    margin-top: 6px;
                    padding-top: 6px;
                    padding-bottom: 8px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 4px;
                    color: {c['text_primary']};
                }}
            """)
        # 刷新所有输入框样式
        for edit in self._input_widgets:
            edit.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {c['bg_primary']};
                    border: 1px solid {c['border']};
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: {c['text_primary']};
                    min-height: 32px;
                }}
                QLineEdit:focus {{
                    border-color: {c['accent']};
                }}
            """)
        # 刷新所有下拉框样式
        for combo in self._combo_widgets:
            combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {c['bg_primary']};
                    border: 1px solid {c['border']};
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: {c['text_primary']};
                    min-height: 34px;
                }}
                QComboBox:hover {{
                    border-color: {c['accent']};
                }}
                QComboBox:focus {{
                    border-color: {c['accent']};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid {c['text_secondary']};
                    margin-right: 8px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {c['bg_primary']};
                    border: 1px solid {c['border']};
                    color: {c['text_primary']};
                    selection-background-color: {c['accent']};
                }}
            """)
        # 刷新保存按钮
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: #FFFFFF;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        # 刷新按钮图标
        self._set_refresh_icon(self.btn_refresh)
        self._set_save_icon(False)


class LogPanel(Win11Card):
    """日志面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("活动日志")
        title.setFont(app_font(13, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {WIN11_COLORS['text_primary']}")
        title_layout.addWidget(title)

        self.btn_clear = QPushButton("清除")
        self.btn_clear.setFont(app_font(10))
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {WIN11_COLORS['accent']};
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        self.btn_clear.clicked.connect(self.clear)
        title_layout.addWidget(self.btn_clear)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 日志内容
        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {WIN11_COLORS['bg_secondary']};
                border: 1px solid {WIN11_COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {WIN11_COLORS['text_secondary']};
            }}
        """)
        layout.addWidget(self.log_text, 1)

    def add_log(self, message: str, level: str = "info"):
        """添加日志"""
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")

        color = WIN11_COLORS['text_secondary']
        if level == "success":
            color = WIN11_COLORS['success']
        elif level == "warning":
            color = WIN11_COLORS['warning']
        elif level == "error":
            color = WIN11_COLORS['error']

        self.log_text.append(f'<span style="color: {WIN11_COLORS["text_tertiary"]}">[{time_str}]</span> <span style="color: {color}">{message}</span>')

        # 限制行数
        max_lines = 100
        doc = self.log_text.document()
        if doc.blockCount() > max_lines:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def clear(self):
        """清除日志"""
        self.log_text.clear()

    def apply_theme(self):
        """应用主题"""
        c = WIN11_COLORS
        self.setStyleSheet(f"""
            #Win11Card {{
                background-color: {c['card_bg']};
                border-radius: 8px;
                border: 1px solid {c['border']};
            }}
        """)
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {c['accent']};
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['bg_secondary']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 8px;
                color: {c['text_secondary']};
            }}
        """)




class TabButtonPanel(Win11Card):
    """独立的设置/日志切换按钮面板"""

    tab_clicked = Signal(int)  # 0=settings, 1=log

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self.btn_settings = QPushButton()
        self.btn_settings.setFont(app_font(11))
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setMinimumHeight(38)
        self.btn_settings.clicked.connect(lambda: self.tab_clicked.emit(0))

        self.btn_log = QPushButton()
        self.btn_log.setFont(app_font(11))
        self.btn_log.setCursor(Qt.PointingHandCursor)
        self.btn_log.setMinimumHeight(38)
        self.btn_log.clicked.connect(lambda: self.tab_clicked.emit(1))

        layout.addWidget(self.btn_settings)
        layout.addWidget(self.btn_log)
        layout.addStretch()

        self.apply_theme()
        self.set_active(-1)  # 初始化为未激活状态

    def _set_btn_icons(self):
        """设置按钮图标"""
        for btn, icon_name, text in [
            (self.btn_settings, "settings", "设置"),
            (self.btn_log, "log", "日志"),
        ]:
            color = 'icon_default'
            pixmap = svg_icon(icon_name, color, 18)
            if not pixmap.isNull():
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(18, 18))
            btn.setText(text)

    def set_active(self, index: int):
        """设置当前激活的按钮（index=-1 表示全部未激活）"""
        c = WIN11_COLORS
        for btn, idx, icon_name in [
            (self.btn_settings, 0, "settings"),
            (self.btn_log, 1, "log"),
        ]:
            is_active = (index == idx)
            # 激活时用 icon_primary（白/深色），非激活用 icon_default
            icon_color = 'icon_primary' if is_active else 'icon_default'
            pixmap = svg_icon(icon_name, icon_color, 18)
            if not pixmap.isNull():
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(18, 18))
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {c['accent']};
                        border: 1px solid {c['accent']};
                        color: {c['bg_primary']};
                        border-radius: 6px;
                        min-height: 38px;
                        padding: 0 20px;
                    }}
                    QPushButton:hover {{ opacity: 0.85; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {c['bg_tertiary']};
                        border: 1px solid {c['border']};
                        color: {c['text_primary']};
                        border-radius: 6px;
                        min-height: 38px;
                        padding: 0 20px;
                    }}
                    QPushButton:hover {{
                        background: {c['accent_light']};
                        border-color: {c['accent']};
                        color: {c['accent']};
                    }}
                """)

    def apply_theme(self):
        """应用主题"""
        c = WIN11_COLORS
        self.setStyleSheet(f"""
            #Win11Card {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)
        self.set_active(-1)


class SettingsLogPanel(QFrame):
    """设置/日志内容面板（纯内容，无按钮）"""

    # 信号：展开/收起
    panel_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Win11Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # StackedWidget 存放两个面板
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.stack.setStyleSheet(f"""
            QStackedWidget {{
                background: {WIN11_COLORS['bg_primary']};
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
        """)
        layout.addWidget(self.stack)

        # 初始折叠（高度为0）
        self._expanded_index = -1  # -1=折叠状态
        self.setFixedHeight(0)
        self._apply_base_style()

    def _apply_base_style(self):
        c = WIN11_COLORS
        self.setStyleSheet(f"""
            #Win11Card {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)

    def add_settings(self, widget):
        self.stack.addWidget(widget)

    def add_log(self, widget):
        self.stack.addWidget(widget)

    def set_current_index(self, index: int):
        """切换显示指定面板"""
        if self._expanded_index == index and self.stack.height() > 0:
            # 再次点击同一按钮 → 收起
            self._collapse()
        else:
            self._expanded_index = index
            self.stack.setCurrentIndex(index)
            self._expand()

    def _expand(self):
        """展开当前面板"""
        content_h = self.stack.currentWidget().sizeHint().height()
        total_h = max(content_h, 300)
        print(f"    [_expand] total_h={total_h}")
        self.setFixedHeight(total_h)
        self.panel_changed.emit(True)

    def _collapse(self):
        """收起"""
        self._expanded_index = -1
        self.setFixedHeight(0)
        self.panel_changed.emit(False)

    def get_current_index(self) -> int:
        return self._expanded_index

    def apply_theme(self):
        """应用主题"""
        self._apply_base_style()
        c = WIN11_COLORS
        self.stack.setStyleSheet(f"""
            QStackedWidget {{
                background: {c['bg_primary']};
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
        """)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        print("[8.1] Config...")
        self.config = Config()
        print("[8.2] Switcher...")
        self.switcher = get_switcher()
        print("[8.3] Detector...")
        self.detector = MicDetector(self.config)
        print("[8.4] HotkeyManager...")
        self.hotkey_manager = HotkeyManager()
        print("[8.5] TrayManager...")
        self.tray_manager = TrayManager(
            on_show=self.show_window,
            on_quit=self.quit_app,
            on_switch=self.manual_switch,
            on_toggle=self.toggle_monitoring
        )

        self.is_running = False
        self.is_dark_mode = is_dark_mode()

        # 先更新全局主题配色，再创建UI（确保设置面板控件使用正确主题）
        update_theme(self.is_dark_mode)

        print("[8.6] init_ui...")
        self.init_ui()
        print("[8.7] init_tray...")
        self.init_tray()
        print("[8.8] init_detector...")
        self.init_detector()
        print("[8.9] init_hotkeys...")
        self.init_hotkeys()
        print("[8.10] update_devices...")
        self.update_devices()
        print("[8.11] auto start monitoring...")
        self.start_monitoring()
        print("[8.12] Done!")

    def _get_stylesheet(self):
        """获取当前主题的样式表"""
        c = WIN11_COLORS
        return f"""
            QMainWindow, QWidget {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
            }}
            QLabel {{
                color: {c['text_primary']};
            }}
            QPushButton {{
                background-color: {c['bg_primary']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 6px 12px;
                color: {c['text_primary']};
            }}
            QPushButton:hover {{
                border-color: {c['accent']};
            }}
            QLineEdit, QComboBox {{
                background-color: {c['bg_primary']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 4px 8px;
                color: {c['text_primary']};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {c['accent']};
            }}
            QGroupBox {{
                border: 1px solid {c['border']};
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 6px;
                padding-bottom: 8px;
                color: {c['text_primary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                color: {c['text_primary']};
            }}
            QTextEdit {{
                background-color: {c['bg_secondary']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 8px;
                color: {c['text_secondary']};
            }}
        """

    def _apply_theme(self, from_event=False):
        """应用主题到所有组件"""
        # 防止从 changeEvent 触发时的无限循环
        if from_event and hasattr(self, '_applying_theme') and self._applying_theme:
            return
        self._applying_theme = True

        update_theme(self.is_dark_mode)

        # 更新主窗口样式
        self.setStyleSheet(self._get_stylesheet())

        # 重建子组件样式
        self.status_card.apply_theme()
        self.control_panel.apply_theme()
        self.settings_panel.apply_theme()
        self.log_panel.apply_theme()
        self.settings_log_panel.apply_theme()
        self.tab_button_panel.apply_theme()
        self.tab_button_panel.set_active(self.settings_log_panel.get_current_index())

        self._applying_theme = False

    def init_ui(self):
        """初始化UI"""
        print("[8.6.1] setWindowTitle...")
        self.setWindowTitle("音频自动切换工具")

        # 设置窗口图标（绿色耳机 .png，Windows 原生支持 PNG 窗口图标）
        icon_path = Path(__file__).parent.parent / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # 窗口宽度固定
        print("[8.6.2] setSize...")
        self.setMinimumWidth(420)
        self.setMaximumWidth(420)

        # 中心部件
        print("[8.6.3] central widget...")
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # 状态卡片
        print("[8.6.4] StatusCard...")
        self.status_card = StatusCard()
        self.main_layout.addWidget(self.status_card)

        # 控制面板
        print("[8.6.5] ControlPanel...")
        self.control_panel = ControlPanel()
        self.control_panel.switch_clicked.connect(self.manual_switch)
        self.control_panel.toggle_clicked.connect(self.toggle_monitoring)
        self.main_layout.addWidget(self.control_panel)

        # 设置和日志标签页（可折叠）
        print("[8.6.6] SettingsLogPanel...")
        self.settings_log_panel = SettingsLogPanel()
        self.settings_log_panel.panel_changed.connect(self._on_panel_changed)

        # 独立的设置/日志切换按钮行
        print("[8.6.6b] TabButtonPanel...")
        self.tab_button_panel = TabButtonPanel()
        self.tab_button_panel.tab_clicked.connect(self._on_tab_clicked)

        print("[8.6.7] SettingsPanel...")
        self.settings_panel = SettingsPanel(self.config, self.switcher)
        self.settings_panel.settings_changed.connect(self.on_settings_changed)

        print("[8.6.8] LogPanel...")
        self.log_panel = LogPanel()

        self.settings_log_panel.add_settings(self.settings_panel)
        self.settings_log_panel.add_log(self.log_panel)

        # 将切换按钮行加入布局
        self.main_layout.addWidget(self.tab_button_panel, 0)

        print("[8.6.9] add panel...")
        self.main_layout.addWidget(self.settings_log_panel, 0)

        # 关闭到托盘
        self.closeToTray = True

        # 应用初始主题
        print("[8.6.10] _apply_theme...")
        self._apply_theme()

        # 调整窗口大小
        print("[8.6.11] _update_window_size...")
        self._update_window_size()
        print("[8.6.12] init_ui done!")

    def _calculate_window_height(self):
        """计算窗口应有的高度"""
        height = 0
        height += 16 * 2
        height += self.status_card.sizeHint().height() + 12
        height += self.control_panel.sizeHint().height() + 12
        height += self.tab_button_panel.sizeHint().height() + 12
        height += self.settings_log_panel.height()
        return height

    def _update_window_size(self):
        """更新窗口大小"""
        print("    [_update_window_size] calculating...")
        height = 16 * 2
        height += self.status_card.sizeHint().height() + 12
        height += self.control_panel.sizeHint().height() + 12
        height += self.tab_button_panel.sizeHint().height() + 12  # 按钮行高度
        height += self.settings_log_panel.height()  # 内容区（折叠时为0）
        print(f"    [_update_window_size] calculated height={height}")
        self.resize(420, height)
        print("    [_update_window_size] done")

    def _on_panel_changed(self, expanded: bool):
        """面板展开/收起时更新窗口大小"""
        print(f"    [_on_panel_changed] expanded={expanded}")
        if not expanded:
            self.tab_button_panel.set_active(-1)
        QTimer.singleShot(0, self._update_window_size)

    def _on_tab_clicked(self, index: int):
        """点击设置/日志切换按钮"""
        self.settings_log_panel.set_current_index(index)
        self.tab_button_panel.set_active(index)

    def changeEvent(self, event):
        """检测系统主题变化"""
        if event.type() == QEvent.PaletteChange:
            self.is_dark_mode = is_dark_mode()
            self._apply_theme(from_event=True)
        super().changeEvent(event)

    def showEvent(self, event):
        """窗口显示时自动调整大小"""
        super().showEvent(event)
        # 确保窗口使用正确的初始高度
        QTimer.singleShot(0, self._update_window_size)

    def init_tray(self):
        """初始化托盘（显示已有的 TrayManager）"""
        # 延迟启动托盘，避免阻塞主窗口初始化
        QTimer.singleShot(100, self.tray_manager.show)

    def init_detector(self):
        """初始化检测器"""
        self.detector.on_status_change = self.on_status_change
        self.detector.on_volume_change = self.on_volume_change

    def init_hotkeys(self):
        """初始化快捷键"""
        hotkey_switch = self.config.get('hotkey_switch', 'ctrl+shift+h')
        self.hotkey_manager.register(hotkey_switch, self.toggle_device)

    def toggle_monitoring(self):
        """切换监控状态"""
        if self.is_running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        """开始监控"""
        if self.detector.start():
            self.is_running = True
            self.control_panel.set_running(True)
            self.log_panel.add_log("开始监听麦克风", "success")
            self.status_card.update_status(False, True)

            if self.config.get('show_notifications'):
                self.tray_manager.notify("音频切换工具", "开始监听...")
        else:
            self.log_panel.add_log("启动失败，请检查麦克风", "error")

    def stop_monitoring(self):
        """停止监控"""
        self.detector.stop()
        self.is_running = False
        self.control_panel.set_running(False)
        self.log_panel.add_log("已停止监听")
        self.status_card.update_status(False, False)

    def on_status_change(self, is_active: bool):
        """状态变化回调"""
        self.status_card.update_status(is_active, True)

        if self.config.get('auto_switch', True):
            device = self.config.get('headphone_name') if is_active else self.config.get('speaker_name')
            success = self.switcher.switch_to_device(device)

            if is_active:
                self.log_panel.add_log(f"麦克风活跃 → 切换到耳机", "success")
                if self.config.get('show_notifications'):
                    self.tray_manager.notify("耳机已打开", "已自动切换到耳机设备")
            else:
                self.log_panel.add_log(f"麦克风静音 → 切换到扬声器", "success")
                if self.config.get('show_notifications'):
                    self.tray_manager.notify("扬声器已打开", "已自动切换到扬声器设备")

    def on_volume_change(self, volume: float, has_sound: bool):
        """音量变化回调"""
        self.status_card.update_volume(volume, self.detector.threshold)

    def toggle_device(self):
        """快捷键切换：在耳机和扬声器之间切换"""
        current = self.switcher.get_default_playback_device()
        headphone = self.config.get('headphone_name', '')
        speaker = self.config.get('speaker_name', '')
        if current and headphone in current:
            self.log_panel.add_log(f"当前是耳机，切换到扬声器")
            self.manual_switch("speaker")
        else:
            self.log_panel.add_log(f"当前是扬声器，切换到耳机")
            self.manual_switch("headphone")

    def manual_switch(self, target: str):
        """手动切换"""
        if target == "headphone":
            device = self.config.get('headphone_name')
            self.log_panel.add_log(f"手动切换 → 耳机", "success")
        else:
            device = self.config.get('speaker_name')
            self.log_panel.add_log(f"手动切换 → 扬声器", "success")

        self.switcher.switch_to_device(device)
        self.update_devices()

        if self.config.get('show_notifications'):
            name = "耳机" if target == "headphone" else "扬声器"
            self.tray_manager.notify(f"已切换到{name}", device)

    def on_settings_changed(self, config_data: dict):
        """设置变化"""
        self.detector.update_config()

        # 重新注册快捷键
        self.hotkey_manager.unregister_all()
        hotkey_switch = config_data.get('hotkey_switch', 'ctrl+shift+h')
        self.hotkey_manager.register(hotkey_switch, self.toggle_device)

        self.log_panel.add_log("设置已更新", "success")

    def update_devices(self):
        """更新设备信息"""
        current = self.switcher.get_default_playback_device()
        if current:
            self.status_card.device_label.setText(f"当前设备: {current}")
            self.log_panel.add_log(f"检测到设备: {current}")

    def show_window(self):
        """显示窗口（从托盘恢复）"""
        # Windows 上如果窗口被 hide() 后，需要先恢复窗口状态
        if self.isMinimized():
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        """退出程序"""
        self.stop_monitoring()
        self.hotkey_manager.unregister_all()
        if self.tray_manager:
            self.tray_manager.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """关闭事件"""
        if self.closeToTray:
            event.ignore()
            self.hide()
            if self.config.get('show_notifications'):
                self.tray_manager.notify("已最小化到托盘", "点击托盘图标可重新打开")
        else:
            self.quit_app()
