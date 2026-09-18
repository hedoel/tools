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
        ok_text: str = "我知道了"
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(440)
        self.setMaximumWidth(560)
        
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

        if headline:
            lbl_headline = QLabel(headline)
            lbl_headline.setFont(QFont("JetBrains Mono", 13, QFont.Bold))
            lbl_headline.setStyleSheet("color: #0F172A;")
            lbl_headline.setWordWrap(True)
            text_layout.addWidget(lbl_headline)

        if message:
            lbl_msg = QLabel(message)
            lbl_msg.setFont(QFont("JetBrains Mono", 10))
            lbl_msg.setStyleSheet("color: #475569; line-height: 1.5;")
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
    def warning(cls, parent, title: str, headline: str, message: str = "", ok_text: str = "知道了"):
        dlg = cls(parent, title, headline, message, icon_type=cls.ICON_WARNING, ok_text=ok_text)
        return dlg.exec_()

    @classmethod
    def information(cls, parent, title: str, headline: str, message: str = "", ok_text: str = "确定"):
        dlg = cls(parent, title, headline, message, icon_type=cls.ICON_SUCCESS, ok_text=ok_text)
        return dlg.exec_()

    @classmethod
    def critical(cls, parent, title: str, headline: str, message: str = "", ok_text: str = "确定"):
        dlg = cls(parent, title, headline, message, icon_type=cls.ICON_ERROR, ok_text=ok_text)
        return dlg.exec_()
