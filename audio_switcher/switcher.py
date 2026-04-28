# -*- coding: utf-8 -*-
"""音频设备切换器"""
import subprocess
import time
import tempfile
import os
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IMMDeviceEnumerator, IMMDevice

# Windows 创建进程标志：不弹出控制台窗口
CREATE_NO_WINDOW = 0x08000000


# PowerShell 脚本：获取播放设备
PS_GET_DEVICES = r"""
Get-PnpDevice -Class 'AudioEndpoint' -Status OK | ForEach-Object {
    $id = $_.InstanceId
    if ($id -match '\{0\.0\.0\.') {
        $_.FriendlyName
    }
}
"""

# PowerShell 脚本：切换设备（通过禁用/启用）
def _ps_switch_device(device_name: str) -> str:
    return rf"""
$device = Get-PnpDevice -Class 'AudioEndpoint' -FriendlyName '*' -Status OK |
    Where-Object {{ $_.FriendlyName -like '*{device_name}*' }} |
    Select-Object -First 1

if ($device) {{
    $device | Disable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 200
    $device | Enable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 200
    Write-Output 'OK'
}} else {{
    Write-Output 'NOT_FOUND'
}}
"""


class AudioSwitcher:
    """音频设备切换器 - 基于 Windows Core Audio API"""

    def __init__(self):
        self.enumerator = None
        self._ps_script_dir = tempfile.gettempdir()
        self._init_enumerator()

    def _init_enumerator(self):
        """初始化设备枚举器"""
        try:
            self.enumerator = AudioUtilities.GetDeviceEnumerator()
        except Exception as e:
            print(f"初始化设备枚举器失败: {e}")

    def _run_ps_script(self, script: str, timeout=10) -> str:
        """通过临时 .ps1 文件执行 PowerShell 脚本，避免命令行转义问题"""
        try:
            # 使用 ANSI 编码临时文件，避免中文路径问题
            ps_file = os.path.join(self._ps_script_dir, 'audio_switcher_temp.ps1')
            with open(ps_file, 'w', encoding='utf-8-sig') as f:
                f.write(script)
            result = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps_file],
                capture_output=True,
                timeout=timeout,
                creationflags=CREATE_NO_WINDOW
            )
            return result.stdout.decode('utf-8-sig', errors='ignore').strip()
        except Exception as e:
            print(f"PowerShell 执行失败: {e}")
            return ""
        finally:
            try:
                if os.path.exists(ps_file):
                    os.remove(ps_file)
            except:
                pass

    def get_playback_devices(self):
        """获取所有播放设备"""
        devices = []

        # 方法1: 使用 pycaw (更快，更可靠)
        try:
            all_devices = AudioUtilities.GetAllDevices()
            for device in all_devices:
                try:
                    # Flow == 0 表示播放设备(eRender)，Flow == 1 表示录制设备(eCapture)
                    if device.Flow == 0:
                        devices.append({
                            'name': device.FriendlyName,
                            'id': device.id,
                        })
                except:
                    pass
        except Exception as e:
            print(f"pycaw 获取设备失败: {e}")

        # 如果 pycaw 失败或数量不足，使用 PowerShell 作为备选/补充
        if len(devices) < 2:
            try:
                output = self._run_ps_script(PS_GET_DEVICES, timeout=5)
                lines = output.strip().split('\n')
                for line in lines:
                    name = line.strip()
                    if name and name not in [d['name'] for d in devices]:
                        devices.append({
                            'name': name,
                            'id': name,
                        })
            except Exception as e:
                print(f"PowerShell 获取设备失败: {e}")

        return devices

    def get_default_playback_device(self):
        """获取当前默认播放设备名称"""
        try:
            # 方法1: 用 pycaw 的 GetAllDevices 找默认
            # 遍历设备列表，找到默认播放设备
            devices = AudioUtilities.GetAllDevices()
            for dev in devices:
                try:
                    if dev.Flow == 0:  # eRender = 播放设备
                        # 检查是否是默认设备
                        if hasattr(dev, 'State') and dev.State == 1:  # DEVICE_STATE_ACTIVE
                            # 尝试通过 IMMDeviceEnumerator 判断默认
                            pass
                except:
                    pass
        except:
            pass

        # 方法2: 用 PowerShell（可靠）
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 '(Get-AudioDevice -Playback | Where-Object {$_.Default -eq $true}).Name'],
                capture_output=True, timeout=5,
                creationflags=CREATE_NO_WINDOW
            )
            name = result.stdout.decode('utf-8', errors='ignore').strip()
            if name:
                return name
        except:
            pass

        # 方法3: 简单的 PowerShell fallback
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 "$dev = Get-CimInstance Win32_SoundDevice | Where-Object {$_.Status -eq 'OK'} | Select-Object -First 1; $dev.Name"],
                capture_output=True, timeout=5,
                creationflags=CREATE_NO_WINDOW
            )
            name = result.stdout.decode('utf-8', errors='ignore').strip()
            if name:
                return name
        except:
            pass

        return None

    def switch_to_device(self, device_name: str) -> bool:
        """切换到指定设备"""
        # 方法1: 使用 PowerShell AudioDeviceCmdlets
        if self._switch_via_powershell(device_name):
            return True

        # 方法2: 使用禁用/启用方式
        return self._switch_via_toggle(device_name)

    def _switch_via_powershell(self, device_name: str) -> bool:
        """通过 PowerShell AudioDeviceCmdlets 切换设备"""
        try:
            cmd = f'''
            try {{
                Import-Module AudioDeviceCmdlets -ErrorAction Stop
                $device = Get-AudioDevice -List | Where-Object {{ $_.Name -like "*{device_name}*" -and $_.Type -eq "Playback" }}
                if ($device) {{
                    Set-AudioDevice -ID $device.ID
                    Write-Output "OK"
                }} else {{
                    Write-Output "NOT_FOUND"
                }}
            }} catch {{
                Write-Output "MODULE_NOT_FOUND"
            }}
            '''

            result = subprocess.run(
                ['powershell', '-Command', cmd],
                capture_output=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW
            )

            output = result.stdout.decode('utf-8', errors='ignore').strip()
            if "OK" in output:
                return True
            if "MODULE_NOT_FOUND" in output:
                # 自动安装模块
                if self._install_audiodevice_module():
                    # 再次尝试
                    return self._switch_via_powershell(device_name)
        except Exception as e:
            print(f"PowerShell 切换失败: {e}")
        return False

    def _install_audiodevice_module(self) -> bool:
        """安装 AudioDeviceCmdlets 模块"""
        try:
            cmd = '''
            Install-Module -Name AudioDeviceCmdlets -Scope CurrentUser -Force -SkipPublisherCheck -ErrorAction SilentlyContinue
            if (Get-Module -ListAvailable -Name AudioDeviceCmdlets) {
                Write-Output "INSTALLED"
            }
            '''
            result = subprocess.run(
                ['powershell', '-Command', cmd],
                capture_output=True,
                timeout=60,
                creationflags=CREATE_NO_WINDOW
            )
            return "INSTALLED" in result.stdout.decode('utf-8', errors='ignore')
        except:
            return False

    def _switch_via_toggle(self, device_name: str) -> bool:
        """通过禁用/启用设备来切换"""
        script = _ps_switch_device(device_name)
        output = self._run_ps_script(script, timeout=15)
        return "OK" in output

    def list_devices(self):
        """列出所有播放设备"""
        print("\n=== 可用播放设备 ===")
        devices = self.get_playback_devices()
        current = self.get_default_playback_device()
        for i, dev in enumerate(devices):
            marker = " <- 当前" if dev['name'] == current else ""
            print(f"  {i+1}. {dev['name']}{marker}")
        print()
        return devices


# 全局实例
_switcher = None


def get_switcher() -> AudioSwitcher:
    """获取切换器实例"""
    global _switcher
    if _switcher is None:
        _switcher = AudioSwitcher()
    return _switcher
