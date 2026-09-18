import json
import os

from utils.crypto import decrypt_secret, encrypt_secret
from utils.paths import config_path, legacy_config_path

DEFAULT_CONFIG = {
    "emp_id": "",
    "remember_emp_id": False,
    "saved_password_enc": "",
    "remember_password": False,
    "weekday_end": "17:30",
    "weekday_ot_start": "18:00",
    "ot_latest_end": "02:00",
    "min_ot_minutes": 30,
    "granularity_minutes": 30,
    "exclude_public_holiday": True,
    "include_weekend_base": True,
    "theme": "light",
    "window_opacity": 100,
    "bg_image_path": "",
    "mask_density": 20,
    "blur_radius": 0,
    "close_action": "tray",
    "custom_export_path": "",
    "edge_path": "",
    "awake_enabled": False,
    "awake_mode": "indefinite",
    "awake_hours": 2,
    "autostart": False,
    "start_minimized": False,
    "debug_mode": False,
    "show_scrollbar": False
}


def _read_json(path: str):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else None
    except Exception:
        return None


def load_config() -> dict:
    """
    读取用户配置 (%APPDATA%/NoOvertime/config.json)
    并自动完成两项一次性迁移:
    1. 旧版写在工作目录/安装目录的 config.json
    2. 旧版明文 saved_password -> DPAPI 密文 saved_password_enc
    3. 首次启动或保存的 Edge 路径失效时，自动寻找系统 Edge 路径并持久化至配置
    """
    raw = _read_json(config_path())
    migrated = False
    if raw is None:
        raw = _read_json(legacy_config_path())
        if raw is None:
            raw = {}
        else:
            migrated = True

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(raw)

    # 首次启动或保存的 Edge 路径不存在时，智能探测系统 Edge 路径并持久化
    saved_edge = str(cfg.get("edge_path", "")).strip()
    if not saved_edge or not os.path.exists(saved_edge):
        try:
            from core.edge_cdp import find_edge_binary
            detected = find_edge_binary()
            if detected and os.path.exists(detected):
                cfg["edge_path"] = detected
                migrated = True
        except Exception:
            pass

    # 旧版「开机自启」隐含静默进托盘，拆分为独立开关后保留原有行为
    if "start_minimized" not in raw:
        cfg["start_minimized"] = bool(cfg.get("autostart", False))
        if cfg["start_minimized"]:
            migrated = True

    legacy_plain = cfg.pop("saved_password", "")
    if legacy_plain:
        cfg["saved_password_enc"] = encrypt_secret(str(legacy_plain))
        migrated = True
    elif "saved_password" in raw:
        migrated = True

    if migrated:
        save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    path = config_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print(f"Error saving config: {e}")


def get_saved_password(cfg: dict) -> str:
    """取出已保存的密码明文 (仅内存使用，磁盘上始终是 DPAPI 密文)"""
    return decrypt_secret(cfg.get("saved_password_enc", ""))


def set_saved_password(cfg: dict, password: str) -> None:
    """写入待保存的密码 (自动加密)；传空串表示清除"""
    cfg["saved_password_enc"] = encrypt_secret(password) if password else ""
    cfg.pop("saved_password", None)
