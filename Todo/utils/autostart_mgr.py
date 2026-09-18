import os
import sys
import winreg

from utils.paths import project_root

APP_NAME = "NoOvertime"
REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_autostart_enabled() -> bool:
    """检查当前是否已在注册表设置开机自启"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False


def set_autostart(enabled: bool, start_minimized: bool = False) -> bool:
    """
    配置开机自启状态（写入或删除 HKCU Run 注册表键）

    :param enabled: 是否开机自启
    :param start_minimized: 是否在启动时静默进入系统托盘 (附加 --tray 参数)，
                            与开机自启彼此独立
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_RUN_PATH,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_READ
        )

        if enabled:
            tray_arg = " --tray" if start_minimized else ""
            if getattr(sys, "frozen", False):
                # 打包后的独立 EXE 运行环境
                exe_path = os.path.abspath(sys.executable)
                cmd = f'"{exe_path}"{tray_arg}'
            else:
                # 源码开发环境：若存在编译产物优先使用，否则使用 python main.py
                # 路径一律基于工程根目录解析，避免受当前工作目录影响
                dist_exe = os.path.join(project_root(), "dist", "NoOvertime", "NoOvertime.exe")
                if os.path.exists(dist_exe):
                    cmd = f'"{dist_exe}"{tray_arg}'
                else:
                    main_py = os.path.join(project_root(), "main.py")
                    cmd = f'"{sys.executable}" "{main_py}"{tray_arg}'

            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass

        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error setting autostart in registry: {e}")
        return False
