import os
import sys

APP_NAME = "NoOvertime"
CONFIG_FILE_NAME = "config.json"


def project_root() -> str:
    """源码工程根目录 (src 的上一级或当前目录)"""
    current_dir = os.path.dirname(os.path.abspath(__file__))  # src/utils
    parent_dir = os.path.dirname(current_dir)                 # src
    if os.path.basename(parent_dir) == "src":
        return os.path.dirname(parent_dir)
    return parent_dir


def exe_dir() -> str:
    """打包后 EXE 所在目录；源码运行时返回工程根目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return project_root()


def resource_path(*parts: str) -> str:
    """
    定位随程序分发的静态资源 (img / driver 等)
    绝不依赖当前工作目录，因此开机自启 (cwd 为 System32) 时同样可用
    """
    rel = os.path.join(*parts)
    candidates = []
    if getattr(sys, "frozen", False):
        mei = getattr(sys, "_MEIPASS", "")
        base = exe_dir()
        candidates.extend([mei, base, os.path.join(base, "_internal")])
    candidates.append(project_root())
    candidates.append(os.getcwd())

    for base in candidates:
        if not base:
            continue
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
    return os.path.join(project_root(), rel)


def app_data_dir() -> str:
    """用户级可写数据目录: %APPDATA%\\NoOvertime"""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        return project_root()
    return d


def config_path() -> str:
    """配置文件的唯一权威位置 (可写、与安装目录解耦)"""
    return os.path.join(app_data_dir(), CONFIG_FILE_NAME)


def legacy_config_path() -> str:
    """
    历史版本把 config.json 写在工作目录/安装目录，
    这里返回首个存在的旧配置文件用于一次性迁移，找不到则返回空字符串
    """
    for base in [os.getcwd(), exe_dir(), project_root()]:
        p = os.path.join(base, CONFIG_FILE_NAME)
        if os.path.abspath(p) == os.path.abspath(config_path()):
            continue
        if os.path.exists(p):
            return p
    return ""
