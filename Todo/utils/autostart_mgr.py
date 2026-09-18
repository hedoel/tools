import os
import sys
import winreg

from utils.paths import project_root

APP_NAME = "NoOvertime"
REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_current_command(start_minimized: bool = False) -> str:
    """获取当前程序启动命令"""
    tray_arg = " --tray" if start_minimized else ""
    if getattr(sys, "frozen", False):
        exe_path = os.path.abspath(sys.executable)
        return f'"{exe_path}"{tray_arg}'
    else:
        dist_exe = os.path.join(project_root(), "dist", "NoOvertime", "NoOvertime.exe")
        if os.path.exists(dist_exe):
            return f'"{dist_exe}"{tray_arg}'
        else:
            main_py = os.path.join(project_root(), "main.py")
            return f'"{sys.executable}" "{main_py}"{tray_arg}'


def _extract_target_exe(cmd: str) -> str:
    """从自启命令中提取目标可执行文件路径"""
    cmd = cmd.strip()
    if cmd.startswith('"'):
        end_idx = cmd.find('"', 1)
        if end_idx != -1:
            return cmd[1:end_idx]
    return cmd.split()[0] if cmd else ""


def is_autostart_enabled() -> bool:
    """
    检查当前是否已在注册表设置开机自启 (B6)
    不仅校验键是否存在，还校验其指向的文件是否存在且与当前运行文件是否一致；
    若文件已移动，则自动修正为当前最新路径，防止静默失效。
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        if not val:
            winreg.CloseKey(key)
            return False

        reg_exe = _extract_target_exe(val)
        current_cmd = get_current_command()
        current_exe = _extract_target_exe(current_cmd)

        # 若注册表中的 exe 路径不存在，说明程序已被移动或删除
        if not os.path.exists(reg_exe):
            if os.path.exists(current_exe):
                # 自动修正注册表为当前程序路径，保留原有 --tray 参数
                has_tray = "--tray" in val
                new_cmd = get_current_command(start_minimized=has_tray)
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, new_cmd)
                winreg.CloseKey(key)
                return True
            winreg.CloseKey(key)
            return False

        # 若注册表路径与当前运行的 exe 路径不一致，自动同步更新
        if os.path.normcase(os.path.abspath(reg_exe)) != os.path.normcase(os.path.abspath(current_exe)):
            if os.path.exists(current_exe):
                has_tray = "--tray" in val
                new_cmd = get_current_command(start_minimized=has_tray)
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, new_cmd)

        winreg.CloseKey(key)
        return True
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
            cmd = get_current_command(start_minimized=start_minimized)
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
