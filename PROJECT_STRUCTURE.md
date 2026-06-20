# 项目结构文档

本文档描述「音频自动切换工具」的目录结构、模块职责、数据流以及关键设计决策，便于新接手者快速建立全局认知。

## 一、目录结构

```
audio_switcher/                        项目根目录
├── run.py                             唯一启动入口（spec 入口）
├── audio_switcher.spec                PyInstaller 打包配置
├── requirements.txt                   Python 依赖清单
├── icon.png                           窗口图标（PNG，主用）
├── icon.ico                           任务栏/资源管理器图标（ICO，Pillow 生成）
├── debug_start.py                     分步调试启动脚本（开发用，带 print）
│
├── audio_switcher/                    源码包
│   ├── __init__.py                    包标识
│   ├── config.py                      配置管理（JSON 持久化）
│   ├── detector.py                    麦克风音量检测
│   ├── switcher.py                    音频设备切换（多重回退）
│   ├── hotkey.py                      全局快捷键
│   ├── tray.py                        系统托盘
│   ├── main_window.py                 主窗口 UI（PySide6）
│   └── check_devices.py               设备检测调试脚本
│
├── icon/                              SVG 图标资源目录（11 个）
│   ├── 24gf-headphones.svg
│   ├── icon_设置.svg
│   ├── 使用文档.svg
│   ├── 保存.svg
│   ├── 停止-outline.svg
│   ├── 刷新.svg
│   ├── 声音开.svg
│   ├── 声音静音.svg
│   ├── 开始-outline.svg
│   ├── 控件.svg
│   └── 暂停-outline.svg
│
├── 设计参考/                          UI 设计规范文档
│   ├── VISUAL_DESIGN.md               Linear Design System 视觉规范
│   └── Design System Inspiration of Linear.md
│
├── build/                             PyInstaller 中间产物（gitignore）
├── dist/                              打包成品输出目录（gitignore）
│   └── 音频自动切换工具.exe
└── .workbuddy/                        AI 助手工作目录（gitignore）
```

## 二、模块职责

| 模块 | 类 | 职责 | 关键依赖 |
|------|-----|------|----------|
| `config.py` | `Config` | 配置读写，存于 `~/.audio_switcher/config.json` | 标准库 json/pathlib |
| `detector.py` | `MicDetector` | 采集麦克风音频，计算 RMS，阈值+防抖判定「说话/静音」 | sounddevice, numpy |
| `switcher.py` | `AudioSwitcher` | 枚举播放设备、切换默认设备（带多重回退） | pycaw, comtypes, PowerShell |
| `hotkey.py` | `HotkeyManager` | 注册/注销全局快捷键 | keyboard |
| `tray.py` | `TrayManager` | 系统托盘图标、右键菜单、左键唤起窗口 | pystray, Pillow |
| `main_window.py` | `MainWindow` 等 | 主窗口 UI、状态显示、设置面板、日志面板、模块协调 | PySide6 |
| `check_devices.py` | — | 命令行调试工具，列出当前播放设备 | switcher |

### 模块依赖关系

```
run.py
  └─ MainWindow (main_window.py)
       ├─ Config (config.py)              ← 配置读写
       ├─ MicDetector (detector.py)       ← 音量回调 → 状态变化
       ├─ AudioSwitcher (switcher.py)     ← 切换设备
       ├─ TrayManager (tray.py)           ← 托盘交互（跨线程 Signal）
       └─ HotkeyManager (hotkey.py)       ← 全局快捷键
```

`MainWindow` 是唯一的协调中心：持有上述所有对象，连接信号槽，把「麦克风状态变化」翻译成「设备切换动作」。

## 三、核心数据流

```
麦克风声音
    │
    ▼
MicDetector._audio_callback          每个音频块（1秒@16kHz）
    │  volume = RMS(indata)
    │  has_sound = volume ≥ threshold
    │
    ├─ 有声音 → silent_count=0, mic_active=True
    └─ 无声音 → silent_count++，累计达 silent_count_threshold(默认6) → mic_active=False
    │
    ▼ (状态翻转时)
on_status_change(mic_active)
    │
    ▼
MainWindow._on_mic_status(active)
    │  active=True  → switch_to_device(headphone_name)   切到耳机
    │  active=False → switch_to_device(speaker_name)     切回扬声器
    │
    ▼
AudioSwitcher.switch_to_device(name)
    ├─ 方法1: PowerShell + AudioDeviceCmdlets 模块（自动安装缺失模块）
    └─ 方法2: 禁用/启用 PnP 设备（Disable-PnpDevice / Enable-PnpDevice）
```

**防抖机制**：`silent_count` 默认 6，配合 `blocksize=16000`（1 秒一块），意味着连续静音约 6 秒才会从「说话」切到「静音」。避免说一句话停顿一下就抖动切换。但「有声音」是即时触发的（一旦音量达标立刻判活跃）。

## 四、关键设计决策

### 4.1 跨线程用 Qt Signal 中继（重要踩坑）

`pystray` 的回调（菜单点击、`on_activate`）运行在 pystray 自己的线程里，该线程**没有 Qt 事件循环**。直接调用 Qt UI 操作（`show()`/`activateWindow()`）会导致白屏卡死；`QTimer.singleShot` 从该线程调用也不会执行。

**解决方案**（`tray.py`）：定义 `_TraySignals(QObject)`，用 4 个 Qt Signal 把所有 pystray 回调投递回主线程。Qt Signal 自动走 `QueuedConnection`，线程安全。

```python
class _TraySignals(QObject):
    show_requested = Signal()
    quit_requested = Signal()
    switch_requested = Signal(str)
    toggle_requested = Signal()
```

所有 pystray 菜单项的 lambda 都改为 `emit()` 信号，而非直接调回调。

### 4.2 subprocess 静默（exe 打包必读）

打包成 exe 后，`subprocess.run` 调 PowerShell 会弹出黑色控制台窗口。全局统一加：

```python
CREATE_NO_WINDOW = 0x08000000
subprocess.run([...], creationflags=CREATE_NO_WINDOW)
```

深色模式检测也优先用 `winreg` 读注册表，而非 PowerShell，进一步减少子进程调用。

### 4.3 设备切换的多重回退

`switcher.py` 的 `switch_to_device()` 有两层回退：

1. **首选**：PowerShell `AudioDeviceCmdlets` 模块 → `Set-AudioDevice`。如果模块未安装，会自动 `Install-Module`（CurrentUser 作用域）后重试。
2. **回退**：通过 `Disable-PnpDevice` + `Enable-PnpDevice` 禁用/启用目标设备，强制系统切换默认设备。

枚举设备时同样回退：优先 `pycaw`（快），不足 2 个时补充 PowerShell `Get-PnpDevice`。

### 4.4 UI 主题实时跟随系统

`MainWindow.changeEvent` 监听 `QEvent.PaletteChange`，系统切换深浅色时立即重算 `is_dark_mode()` 并 `_apply_theme()`，无需重启。`is_dark_mode()` 读注册表 `AppsUseLightTheme`。

### 4.5 SVG 图标动态着色

`icon/` 下的 SVG 通过 `QSvgRenderer` 加载，部分文件没有 `fill` 属性，需要 regex 二次注入当前主题色后再渲染，实现「亮色模式深色图标 / 暗色模式浅色图标」。

### 4.6 ICO 生成

窗口图标用 PNG；ICO 用 Pillow 原生 `img.save('icon.ico', append_images=...)` 生成。Pillow 会自动对小尺寸用 BMP 编码（Windows 资源管理器兼容）、大尺寸用 PNG。16×16 需极度简化绘制（纯方块耳罩，无圆角），不能用大图缩小。

## 五、配置项详解

配置文件：`~/.audio_switcher/config.json`，首次运行自动创建。

| 键 | 默认值 | 说明 |
|----|--------|------|
| `threshold` | `0.005` | 音量判定阈值（RMS），低于此值视为静音 |
| `sample_rate` | `16000` | 麦克风采样率 |
| `blocksize` | `16000` | 音频块大小（=采样率时为 1 秒一块） |
| `silent_count` | `6` | 连续静音多少块后判定为静音状态（约 6 秒） |
| `headphone_name` | `扬声器 (AKG N9 Hybrid)` | 耳机设备名（需与系统设备名匹配） |
| `speaker_name` | `扬声器 (EDIFIER N300)` | 扬声器设备名 |
| `auto_switch` | `True` | 是否启用自动切换 |
| `show_notifications` | `True` | 切换时显示系统通知 |
| `start_minimized` | `False` | 启动时最小化到托盘 |
| `auto_start` | `False` | 开机自启 |
| `hotkey_switch` | `ctrl+shift+h` | 切换设备快捷键 |
| `hotkey_toggle` | `ctrl+shift+t` | 配置预留（UI 暂未暴露） |

## 六、打包链路

```
audio_switcher.spec
    │
    ├─ 入口: run.py
    ├─ 数据: icon/ 目录 + icon.png + icon.ico
    ├─ hiddenimports: PySide6.QtSvg, pycaw, comtypes, sounddevice,
    │                 numpy, keyboard, pystray, PIL
    ├─ excludes: tkinter, matplotlib, scipy, pandas, pytest, unittest, IPython
    └─ 输出: dist/音频自动切换工具.exe (单文件, 无控制台, UPX 压缩)
```

打包命令：`pyinstaller audio_switcher.spec`
