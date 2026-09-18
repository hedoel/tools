import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from gui.main_window import MainWindow
from utils.paths import resource_path

def main():
    # 启用高分屏 (High DPI) 缩放与自适应
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    
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
    
    # 静默进入托盘的两个来源: 启动参数、首选项中的「启动后隐藏到系统托盘」
    start_in_tray = (
        any(arg in sys.argv for arg in ["--tray", "--minimized", "--silent"])
        or bool(window.config.get("start_minimized", False))
    )
    if start_in_tray:
        window.notify_started_in_tray()
    else:
        window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
