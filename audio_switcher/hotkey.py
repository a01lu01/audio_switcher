# -*- coding: utf-8 -*-
"""全局快捷键管理器"""
import threading
from typing import Callable, Optional, Dict


class HotkeyManager:
    """全局快捷键管理器"""

    def __init__(self):
        self.hotkeys: Dict[str, Callable] = {}
        self.running = False
        self.thread = None

    def register(self, key: str, callback: Callable):
        """注册快捷键"""
        try:
            import keyboard
            # 取消之前的绑定
            if key in self.hotkeys:
                keyboard.remove_hotkey(key)

            # 注册新快捷键
            keyboard.add_hotkey(key, callback)
            self.hotkeys[key] = callback
            print(f"已注册快捷键: {key}")
            return True
        except ImportError:
            print("keyboard 模块未安装")
            return False
        except Exception as e:
            print(f"注册快捷键失败: {e}")
            return False

    def unregister(self, key: str):
        """取消注册快捷键"""
        try:
            import keyboard
            if key in self.hotkeys:
                keyboard.remove_hotkey(key)
                del self.hotkeys[key]
        except:
            pass

    def unregister_all(self):
        """取消所有快捷键"""
        try:
            import keyboard
            for key in list(self.hotkeys.keys()):
                keyboard.remove_hotkey(key)
            self.hotkeys.clear()
        except:
            pass

    def reload(self):
        """重新加载所有快捷键"""
        try:
            import keyboard
            # 清除旧的
            for key in list(self.hotkeys.keys()):
                keyboard.remove_hotkey(key)

            # 重新注册
            for key, callback in list(self.hotkeys.items()):
                keyboard.add_hotkey(key, callback)
        except:
            pass
