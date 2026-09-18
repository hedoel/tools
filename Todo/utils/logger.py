import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from utils.paths import exe_dir, app_data_dir

_LOGGER = None


def init_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    # 优先使用安装目录或执行目录下的 logs 文件夹 (相对路径优先)
    log_dir = os.path.join(exe_dir(), "logs")
    writable = False
    try:
        os.makedirs(log_dir, exist_ok=True)
        test_probe = os.path.join(log_dir, ".probe_write")
        with open(test_probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_probe)
        writable = True
    except Exception:
        writable = False

    if not writable:
        # 若安装目录受系统权限保护不可写，回退至 %APPDATA%\NoOvertime\logs
        log_dir = os.path.join(app_data_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "NoOvertime.log")

    logger = logging.getLogger("NoOvertime")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # 轮转日志: 5MB 单文件上限，保留 3 个历史回溯
    handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # 源码或带控制台模式下，同时输出到 stdout
    if sys.stdout and not getattr(sys, "frozen", False):
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        logger.addHandler(console)

    _LOGGER = logger

    # 全局未捕获异常兜底记录 (B8)
    def global_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("未捕获的全局崩溃异常 (Unhandled Exception):", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = global_excepthook

    logger.info(f"=== NoOvertime 日志服务已启动，日志存储路径: {log_file} ===")
    return _LOGGER


def get_logger() -> logging.Logger:
    if _LOGGER is None:
        return init_logger()
    return _LOGGER
