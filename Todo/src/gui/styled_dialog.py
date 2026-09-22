import sys
from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QColor


class StyledMessageBox(QDialog):
    """与应用浅色现代风及 JetBrains Mono 风格完全契合的模态对话框"""

    ICON_WARNING = "warning"
    ICON_INFO = "info"
    ICON_ERROR = "error"
    ICON_SUCCESS = "success"

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "提示",
        headline: str = "",
        message: str = "",
        icon_type: str = "info",
        ok_text: str = "我知道了",
        is_dark: Optional[bool] = None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(440)
        self.setMaximumWidth(560)

        # C3: 自动继承父组件主题或使用传入的主题
        if is_dark is None:
            if parent is not None:
                if hasattr(parent, "is_dark"):
                    is_dark = bool(parent.is_dark)
                elif hasattr(parent, "config") and isinstance(parent.config, dict):
                    is_dark = (parent.config.get("theme", "light") == "dark")
                else:
                    is_dark = False
            else:
                is_dark = False

        self.is_dark = is_dark

        if is_dark:
            # 深色模式样式
            self.setStyleSheet("""
                QDialog {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 10px;
                }
                QLabel {
                    font-family: 'JetBrains Mono', 'Segoe UI', '微软雅黑', sans-serif;
                    color: #CBD5E1;
                }
                QPushButton#btn_dialog_ok {
                    background-color: #3B82F6;
                    color: #FFFFFF;
                    font-family: 'JetBrains Mono', 'Segoe UI', '微软雅黑', sans-serif;
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 7px 22px;
                    border: none;
                }
                QPushButton#btn_dialog_ok:hover {
                    background-color: #2563EB;
                }
                QPushButton#btn_dialog_cancel {
                    background-color: #334155;
                    color: #94A3B8;
                    font-family: 'JetBrains Mono', 'Segoe UI', '微软雅黑', sans-serif;
                    font-size: 13px;
                    border-radius: 6px;
                    padding: 7px 18px;
                    border: 1px solid #475569;
                }
                QPushButton#btn_dialog_cancel:hover {
                    background-color: #475569;
                    color: #F1F5F9;
                }
            """)
        else:
            # 现代浅色样式
            self.setStyleSheet("""
                QDialog {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 10px;
                }
                QLabel {
                    font-family: 'JetBrains Mono', 'Segoe UI', '微软雅黑', sans-serif;
                    color: #334155;
                }
                QPushButton#btn_dialog_ok {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    font-family: 'JetBrains Mono', 'Segoe UI', '微软雅黑', sans-serif;
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 7px 22px;
                    border: none;
                }
                QPushButton#btn_dialog_ok:hover {
                    background-color: #1D4ED8;
                }
                QPushButton#btn_dialog_cancel {
                    background-color: #F8FAFC;
                    color: #64748B;
                    font-family: 'JetBrains Mono', 'Segoe UI', '微软雅黑', sans-serif;
                    font-size: 13px;
                    border-radius: 6px;
                    padding: 7px 18px;
                    border: 1px solid #CBD5E1;
                }
                QPushButton#btn_dialog_cancel:hover {
                    background-color: #F1F5F9;
                    color: #1E293B;
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)

        # 内容区 (图标 + 文本)
        content_box = QHBoxLayout()
        content_box.setSpacing(16)
        content_box.setAlignment(Qt.AlignTop)

        # 现代徽章图标
        badge = QLabel()
        badge.setFixedSize(42, 42)
        badge.setAlignment(Qt.AlignCenter)
        
        if is_dark:
            if icon_type == self.ICON_WARNING:
                badge.setText("⚠️")
                badge.setStyleSheet("background-color: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 21px; font-size: 20px;")
            elif icon_type == self.ICON_ERROR:
                badge.setText("❌")
                badge.setStyleSheet("background-color: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 21px; font-size: 18px;")
            elif icon_type == self.ICON_SUCCESS:
                badge.setText("✅")
                badge.setStyleSheet("background-color: rgba(34, 197, 94, 0.2); border: 1px solid rgba(34, 197, 94, 0.4); border-radius: 21px; font-size: 18px;")
            else:
                badge.setText("ℹ️")
                badge.setStyleSheet("background-color: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 21px; font-size: 18px;")
        else:
            if icon_type == self.ICON_WARNING:
                badge.setText("⚠️")
                badge.setStyleSheet("background-color: #FEF3C7; border: 1px solid #FDE68A; border-radius: 21px; font-size: 20px;")
            elif icon_type == self.ICON_ERROR:
                badge.setText("❌")
                badge.setStyleSheet("background-color: #FEE2E2; border: 1px solid #FECACA; border-radius: 21px; font-size: 18px;")
            elif icon_type == self.ICON_SUCCESS:
                badge.setText("✅")
                badge.setStyleSheet("background-color: #DCFCE7; border: 1px solid #BBF7D0; border-radius: 21px; font-size: 18px;")
            else:
                badge.setText("ℹ️")
                badge.setStyleSheet("background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 21px; font-size: 18px;")
            
        content_box.addWidget(badge)

        # 文本区域
        text_layout = QVBoxLayout()
        text_layout.setSpacing(8)

        headline_color = "#F8FAFC" if is_dark else "#0F172A"
        msg_color = "#94A3B8" if is_dark else "#475569"

        if headline:
            lbl_headline = QLabel(headline)
            lbl_headline.setFont(QFont("JetBrains Mono", 13, QFont.Bold))
            lbl_headline.setStyleSheet(f"color: {headline_color};")
            lbl_headline.setWordWrap(True)
            text_layout.addWidget(lbl_headline)

        if message:
            lbl_msg = QLabel(message)
            lbl_msg.setFont(QFont("JetBrains Mono", 10))
            lbl_msg.setStyleSheet(f"color: {msg_color}; line-height: 1.5;")
            lbl_msg.setWordWrap(True)
            lbl_msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
            text_layout.addWidget(lbl_msg)

        content_box.addLayout(text_layout, 1)
        layout.addLayout(content_box)

        # 底部按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton(ok_text)
        self.btn_ok.setObjectName("btn_dialog_ok")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

    @classmethod
    def warning(cls, parent, title: str, headline: str, message: str = "", ok_text: str = "知道了", is_dark: Optional[bool] = None):
        dlg = cls(parent, title, headline, message, icon_type=cls.ICON_WARNING, ok_text=ok_text, is_dark=is_dark)
        return dlg.exec_()

    @classmethod
    def information(cls, parent, title: str, headline: str, message: str = "", ok_text: str = "确定", is_dark: Optional[bool] = None):
        dlg = cls(parent, title, headline, message, icon_type=cls.ICON_SUCCESS, ok_text=ok_text, is_dark=is_dark)
        return dlg.exec_()

    @classmethod
    def critical(cls, parent, title: str, headline: str, message: str = "", ok_text: str = "确定", is_dark: Optional[bool] = None):
        dlg = cls(parent, title, headline, message, icon_type=cls.ICON_ERROR, ok_text=ok_text, is_dark=is_dark)
        return dlg.exec_()
