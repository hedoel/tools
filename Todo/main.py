import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from gui.main_window import MainWindow
from utils.paths import resource_path
from utils.logger import init_logger
from utils.single_instance import SingleInstanceGuard

def main():
    # 初始化日志系统 (自动定位安装目录或相对路径下的 logs/NoOvertime.log)
    logger = init_logger()

    # 启用高分屏 (High DPI) 缩放与自适应
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    if any(arg in sys.argv for arg in ["--version", "-v"]):
        print("NoOvertime v1.0.0")
        sys.exit(0)

    # 单实例保护 (B7): 若已存在运行实例，通知其激活窗口后退出
    guard = SingleInstanceGuard()
    if guard.is_another_instance_running():
        logger.info("检测到已存在正在运行的 NoOvertime 实例，已请求唤醒该实例并退出当前进程。")
        sys.exit(0)

    # 创建 Windows 命名互斥体，供安装与卸载程序检测是否在运行
    import ctypes
    _app_win32_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "NoOvertime_Application_Mutex")
    
    # 全局设置猫咪图标 (按程序自身位置解析，开机自启时同样有效)
    for name in ["猫咪.png", "icon.ico"]:
        p = resource_path("img", name)
        if os.path.exists(p):
            app.setWindowIcon(QIcon(p))
            break
            
    # 全局设置 JetBrains Mono 字体
    font = QFont("JetBrains Mono", 10)
    font.setStyleHint(QFont.Monospace)
    app.setFont(font)
    
    window = MainWindow()
    # 开启单实例管道监听，后续重复双击将自动激活窗口
    guard.start_listening(window.show_and_activate)
    
    # 检查系统托盘可用性 (B8 边界防护)
    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    if not tray_available:
        logger.warning("当前系统环境未检测到可用的系统托盘服务，强制以窗口模式显示！")

    # 静默进入托盘的两个来源: 启动参数、首选项中的「启动后隐藏到系统托盘」
    start_in_tray = (
        tray_available
        and (
            any(arg in sys.argv for arg in ["--tray", "--minimized", "--silent"])
            or bool(window.config.get("start_minimized", False))
        )
    )
    if start_in_tray:
        window.notify_started_in_tray()
    else:
        window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
