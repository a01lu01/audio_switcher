@echo off
chcp 65001 >nul
title 音频自动切换工具

echo.
echo ========================================
echo     音频自动切换工具 v2.0
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 检查依赖...
pip install -q PySide6 pycaw sounddevice numpy keyboard pystray Pillow

REM 启动
echo [2/3] 启动中...
cd /d "%~dp0"

REM 使用 debug_start.py 启动以便调试
if exist debug_start.py (
    python debug_start.py
) else (
    python run.py
)

pause
