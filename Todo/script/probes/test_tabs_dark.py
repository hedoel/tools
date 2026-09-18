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
    cfg["theme"] = "dark"

    dlg = SettingsDialog(cfg)
    dlg.show()

    # 截图 Tab 3 (常规与行为) 暗色模式
    QTimer.singleShot(500, lambda: switch_and_capture(dlg, 2, "test_tab3_dark.png"))
    QTimer.singleShot(1200, app.quit)

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
