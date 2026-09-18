import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from gui.settings_dialog import SettingsDialog
from utils.config_mgr import load_config

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont("JetBrains Mono", 10)
    app.setFont(font)

    cfg = load_config()
    cfg["theme"] = "light"

    dlg = SettingsDialog(cfg)
    dlg.show()

    # 截图 Tab 1 (Awake) 首先看按钮与TabBar
    QTimer.singleShot(400, lambda: switch_and_capture(dlg, 1, "test_fixed_awake_tab.png"))
    # 截图 Tab 0 (个性化)
    QTimer.singleShot(900, lambda: switch_and_capture(dlg, 0, "test_fixed_appearance_tab.png"))
    # 截图 Tab 2 (启动设置)
    QTimer.singleShot(1400, lambda: switch_and_capture(dlg, 2, "test_fixed_behavior_tab.png"))
    # 退出测试
    QTimer.singleShot(2000, app.quit)

    app.exec_()

def switch_and_capture(dlg, idx, name):
    dlg.tab_widget.setCurrentIndex(idx)
    pix = dlg.grab()
    out_dir = r"C:\Users\128064\.gemini\antigravity-ide\brain\cefe9c2e-ecf5-4e0d-9d2d-c1431ffa95ea"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, name)
    pix.save(out_path)
    print(f"Captured {name} to {out_path}")

if __name__ == "__main__":
    main()
