# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# 项目根目录
ROOT = SPECPATH

a = Analysis(
    [str(Path(ROOT) / 'run.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # SVG 图标目录
        (str(Path(ROOT) / 'icon'), 'icon'),
        # 窗口图标
        (str(Path(ROOT) / 'icon.png'), '.'),
        (str(Path(ROOT) / 'icon.ico'), '.'),
    ],
    hiddenimports=[
        'PySide6.QtSvg',
        'pycaw',
        'comtypes',
        'sounddevice',
        'numpy',
        'keyboard',
        'pystray',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'scipy', 'pandas',
        'pytest', 'unittest', 'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='音频自动切换工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(Path(ROOT) / 'icon.ico'),
)
