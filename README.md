# 音频自动切换工具

一个 Windows 桌面小工具：**监听麦克风，有人说话自动切到耳机，没人说话自动切回扬声器**。避免在家开会/打游戏时声音外放打扰别人，也避免一直戴耳机的疲劳。

开机后静默驻留系统托盘，自动在两套音频输出设备间切换，也支持手动快捷键切换。

## 功能特性

- **自动切换**：实时监听麦克风音量，检测到说话切到耳机，持续静音切回扬声器
- **防抖设计**：静音需持续约 6 秒才切换，避免说话停顿导致频繁抖动；有声音则即时切换
- **系统托盘**：静默驻留，左键唤起主窗口，右键菜单手动切换/退出
- **全局快捷键**：默认 `Ctrl+Shift+H` 一键切换耳机/扬声器
- **亮暗双主题**：跟随系统主题，切换时实时生效，无需重启
- **设置面板**：可视化配置设备名、阈值、静音时长、快捷键、通知、开机自启
- **实时日志**：彩色时间戳日志面板，记录检测与切换事件
- **单文件 exe**：PyInstaller 打包，无控制台窗口，开箱即用

## 系统要求

- Windows 10 / 11
- Python 3.9+（仅开发需要，运行 exe 无需）
- 可用的麦克风（用于声音检测）
- 至少两个音频输出设备（耳机 + 扬声器）

## 快速开始

### 方式一：直接运行 exe

从 [Releases](../../releases) 下载 `音频自动切换工具.exe`，双击运行。程序会静默启动到系统托盘。

### 方式二：从源码运行

```bash
git clone https://github.com/a01lu01/audio_switcher.git
cd audio_switcher
pip install -r requirements.txt
python run.py
```

## 使用说明

1. **首次启动**：程序驻留托盘，左键点击托盘图标打开主窗口
2. **配置设备**：在「设置」面板的下拉框中选择你的耳机和扬声器，点击「保存」
3. **开始监听**：右键托盘 →「开始/停止监听」，或重启程序
4. **自动切换**：对着麦克风说话，声音切到耳机；静默约 6 秒后切回扬声器
5. **手动切换**：按 `Ctrl+Shift+H`，或右键托盘 →「切换到耳机/扬声器」

### 配置项

配置文件位于 `~/.audio_switcher/config.json`，也可在主窗口「设置」面板修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 音量阈值 | 0.005 | RMS 音量低于此值视为静音 |
| 静音判定 | 6 秒 | 持续静音多久后切回扬声器 |
| 耳机设备 | 自动检测 | 检测到说话时切换到此设备 |
| 扬声器设备 | 自动检测 | 静默时切换到此设备 |
| 切换快捷键 | `Ctrl+Shift+H` | 全局快捷键 |
| 通知 | 开启 | 切换时显示系统通知 |
| 开机自启 | 关闭 | 随系统启动 |

## 打包成 exe

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller audio_switcher.spec
```

生成的 exe 在 `dist/音频自动切换工具.exe`。

## 项目结构

详见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)。

```
audio_switcher/
├── run.py                  启动入口
├── audio_switcher.spec     PyInstaller 配置
├── requirements.txt        依赖清单
├── audio_switcher/         源码包
│   ├── config.py           配置管理
│   ├── detector.py         麦克风检测
│   ├── switcher.py         设备切换（多重回退）
│   ├── hotkey.py           全局快捷键
│   ├── tray.py             系统托盘（跨线程 Signal）
│   └── main_window.py      主窗口 UI
├── icon/                   SVG 图标资源
└── 设计参考/                UI 设计规范
```

## 技术栈

| 领域 | 技术 |
|------|------|
| UI 框架 | PySide6（Qt for Python），Win11 / Linear 极简风格 |
| 音频检测 | sounddevice 采集 + numpy 计算 RMS |
| 设备控制 | pycaw + comtypes，PowerShell AudioDeviceCmdlets 回退 |
| 全局快捷键 | keyboard |
| 系统托盘 | pystray + Pillow |
| 打包 | PyInstaller（单文件，UPX 压缩，无控制台） |

## 工作原理

```
麦克风 → RMS 音量计算 → 阈值判定 → 防抖(silent_count) → 状态翻转
                                                          │
                                          说话 → 切到耳机  │  静默 → 切回扬声器
```

设备切换采用多重回退策略：优先 PowerShell `AudioDeviceCmdlets` 模块（缺失自动安装），失败则通过 `Disable-PnpDevice` / `Enable-PnpDevice` 禁用启用设备强制切换。

## 已知限制

- 仅支持 Windows（依赖 pycaw 和 PowerShell）
- 设备名需与系统「声音设置」中的名称精确匹配
- 麦克风阈值需根据实际环境调整，过于灵敏可能误触发
- 首次运行如未安装 `AudioDeviceCmdlets` 模块，首次切换会有几秒延迟（自动安装中）

## License

个人项目，欢迎参考学习。
