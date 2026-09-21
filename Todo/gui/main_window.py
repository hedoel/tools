import sys
import os
import io
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QCheckBox,
    QComboBox, QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QFileDialog, QGroupBox, QFrame, QStackedWidget,
    QSystemTrayIcon, QMenu, QAction, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QPixmap
from PIL import Image, ImageFilter

from utils.config_mgr import load_config, save_config, get_saved_password, set_saved_password
from utils.exporter import export_overtime_to_excel
from utils.paths import resource_path
from core.edge_cdp import EdgeCDPManager
from core.scraper import AttendanceScraper
from core.calculator import calculate_overtime_allowance
from core.awake_mgr import AwakeManager
from gui.styled_dialog import StyledMessageBox
from gui.calendar_view import AttendanceCalendarWidget
from gui.settings_dialog import SettingsDialog


class ScraperThread(QThread):
    """异步后台线程，执行 Selenium 自动化流程 (始终采用静默无头模式)"""
    log_signal = pyqtSignal(str, int)  # 提示信息, 进度百分比
    finished_signal = pyqtSignal(bool, str, str, list, list)  # 成功标志, 员工姓名, 错误信息, 记录列表, 失败日期列表

    def __init__(self, emp_id: str, password: str, year: int, month: int, rules: dict, headless: bool = True, edge_path: str = ""):
        super().__init__()
        self.emp_id = emp_id
        self.password = password
        self.year = year
        self.month = month
        self.rules = rules
        self.headless = headless
        self.edge_path = edge_path
        self.cdp_mgr: Optional[EdgeCDPManager] = None

    def run(self):
        try:
            self.log_signal.emit("Loading...", 5)
            self.cdp_mgr = EdgeCDPManager(
                port=None,
                headless=self.headless,
                edge_bin=self.edge_path,
                progress_callback=lambda msg, pct: self.log_signal.emit(msg, pct)
            )
            driver = self.cdp_mgr.start("https://www.eveportal.com/login")
            
            scraper = AttendanceScraper(
                driver=driver,
                progress_callback=lambda msg, pct: self.log_signal.emit(msg, pct)
            )
            
            # 自动化流程
            scraper.login(self.emp_id, self.password)
            scraper.enter_peoplus_hr()
            scraper.enter_attendance_overview()
            
            emp_name, records, failed_days = scraper.scrape_month_records(
                year=self.year,
                month=self.month,
                calc_rules=self.rules
            )
            
            self.finished_signal.emit(True, emp_name, "", records, failed_days)
        except Exception as e:
            self.finished_signal.emit(False, "", str(e), [], [])
        finally:
            # 彻底释放 Edge 进程与临时目录
            if self.cdp_mgr:
                try:
                    self.cdp_mgr.quit()
                except Exception:
                    pass
                self.cdp_mgr = None


class BackgroundCentralWidget(QWidget):
    """支持自定义背景图片、高斯模糊与遮罩浓度的中心部件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg_pixmap: Optional[QPixmap] = None
        self.mask_density: int = 20
        self.is_dark: bool = False
        # 缩放后的背景缓存：避免每帧重做 SmoothTransformation 缩放
        self._scaled_cache: Optional[QPixmap] = None

    def set_background(self, pixmap: Optional[QPixmap], mask_density: int, is_dark: bool):
        self.bg_pixmap = pixmap
        self.mask_density = mask_density
        self.is_dark = is_dark
        self._scaled_cache = None
        self.update()

    def resizeEvent(self, event):
        self._scaled_cache = None
        super().resizeEvent(event)

    def _scaled_background(self) -> Optional[QPixmap]:
        if not self.bg_pixmap or self.bg_pixmap.isNull():
            return None
        if self._scaled_cache is None or self._scaled_cache.size() != self.size():
            target = self.size()
            if target.isEmpty():
                return None
            self._scaled_cache = self.bg_pixmap.scaled(
                target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
        return self._scaled_cache

    def paintEvent(self, event):
        painter = QPainter(self)
        scaled = self._scaled_background()
        if scaled:
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            
            if self.mask_density > 0:
                alpha = int(255 * (self.mask_density / 100.0))
                color = QColor(15, 23, 42, alpha) if self.is_dark else QColor(248, 250, 252, alpha)
                painter.fillRect(self.rect(), color)
        else:
            bg_color = QColor("#0F172A") if self.is_dark else QColor("#F8FAFC")
            painter.fillRect(self.rect(), bg_color)


# 背景图处理结果缓存 (key: 路径 + 修改时间 + 模糊半径)，只保留最近一次
_BG_CACHE: Dict[tuple, QPixmap] = {}


def load_and_process_bg(image_path: str, blur_radius: int) -> Optional[QPixmap]:
    """使用 Pillow 加载并平滑模糊背景图 (带缓存，避免每次调整设置都重新解码+高斯模糊)"""
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        cache_key = (os.path.abspath(image_path), os.path.getmtime(image_path), int(blur_radius))
    except OSError:
        return None
        
    cached = _BG_CACHE.get(cache_key)
    if cached is not None:
        return cached
        
    try:
        img = Image.open(image_path).convert("RGBA")
        img.thumbnail((2560, 1440), Image.Resampling.LANCZOS)
        if blur_radius > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        pix = QPixmap()
        pix.loadFromData(buf.getvalue())
        _BG_CACHE.clear()
        _BG_CACHE[cache_key] = pix
        return pix
    except Exception as e:
        print(f"Error loading background image: {e}")
        return None


def get_app_stylesheet(is_dark: bool, has_bg: bool) -> str:
    bg_main = "transparent" if has_bg else ("#0F172A" if is_dark else "#F8FAFC")
    card_bg = "rgba(30, 41, 59, 0.88)" if (has_bg and is_dark) else ("rgba(255, 255, 255, 0.90)" if (has_bg and not is_dark) else ("#1E293B" if is_dark else "#FFFFFF"))
    border = "#334155" if is_dark else "#E2E8F0"
    text_color = "#F8FAFC" if is_dark else "#0F172A"
    subtext_color = "#94A3B8" if is_dark else "#334155"
    input_bg = "rgba(15, 23, 42, 0.85)" if (has_bg and is_dark) else ("rgba(255, 255, 255, 0.9)" if (has_bg and not is_dark) else ("#0F172A" if is_dark else "#FFFFFF"))
    input_border = "#475569" if is_dark else "#CBD5E1"
    btn_sec_bg = "#1E293B" if is_dark else "#FFFFFF"
    btn_sec_hover = "#334155" if is_dark else "#F1F5F9"
    grid_color = "#334155" if is_dark else "#F1F5F9"
    th_bg = "#0F172A" if is_dark else "#1E293B"
    rule_bg = "#1E293B" if is_dark else "#EFF6FF"
    rule_border = "#3B82F6" if is_dark else "#BFDBFE"
    rule_text = "#60A5FA" if is_dark else "#1E40AF"
    btn_sec_pressed = "#475569" if is_dark else "#CBD5E1"
    arrow_name = "arrow_down_dark.png" if is_dark else "arrow_down_light.png"
    arrow_down_path = resource_path("img", arrow_name).replace("\\", "/")
    arrow_up_name = "arrow_up_dark.png" if is_dark else "arrow_up_light.png"
    arrow_up_path = resource_path("img", arrow_up_name).replace("\\", "/")

    return f"""
        * {{
            font-family: 'JetBrains Mono', 'Segoe UI', '微软雅黑', sans-serif;
        }}
        QMainWindow {{
            background-color: {bg_main};
        }}
        QWidget#central_widget {{
            background-color: transparent;
        }}
        QGroupBox {{
            background-color: {card_bg};
            border: 1px solid {border};
            border-radius: 8px;
            margin-top: 10px;
            font-size: 13px;
            font-weight: bold;
            color: {text_color};
            padding-top: 16px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            background-color: {card_bg};
            color: {text_color};
        }}
        QLabel {{
            font-size: 13px;
            color: {subtext_color};
        }}
        QLabel#rule_tip {{
            color: {rule_text};
            background: {rule_bg};
            border: 1px solid {rule_border};
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
        }}
        QLineEdit {{
            border: 1px solid {input_border};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 13px;
            background-color: {input_bg};
            color: {text_color};
        }}
        QLineEdit:focus {{
            border: 1.5px solid #2563EB;
        }}
        QSpinBox {{
            border: 1px solid {input_border};
            border-radius: 6px;
            padding: 5px 20px 5px 8px;
            font-size: 13px;
            background-color: {input_bg};
            color: {text_color};
        }}
        QSpinBox:focus {{
            border: 1.5px solid #2563EB;
        }}
        QSpinBox::up-button {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 18px;
            border-left: 1px solid {input_border};
            border-bottom: 0.5px solid {input_border};
            border-top-right-radius: 5px;
            background-color: transparent;
            margin: 1px 1px 0 0;
        }}
        QSpinBox::up-button:hover {{
            background-color: {btn_sec_hover};
        }}
        QSpinBox::up-button:pressed {{
            background-color: {btn_sec_pressed};
        }}
        QSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 18px;
            border-left: 1px solid {input_border};
            border-top: 0.5px solid {input_border};
            border-bottom-right-radius: 5px;
            background-color: transparent;
            margin: 0 1px 1px 0;
        }}
        QSpinBox::down-button:hover {{
            background-color: {btn_sec_hover};
        }}
        QSpinBox::down-button:pressed {{
            background-color: {btn_sec_pressed};
        }}
        QSpinBox::up-arrow {{
            image: url("{arrow_up_path}");
            width: 8px;
            height: 5px;
        }}
        QSpinBox::down-arrow {{
            image: url("{arrow_down_path}");
            width: 8px;
            height: 5px;
        }}
        QComboBox {{
            border: 1px solid {input_border};
            border-radius: 6px;
            padding: 5px 20px 5px 8px;
            font-size: 13px;
            background-color: {input_bg};
            color: {text_color};
        }}
        QComboBox:focus {{
            border: 1.5px solid #2563EB;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 18px;
            border: none;
        }}
        QComboBox::down-arrow {{
            image: url("{arrow_down_path}");
            width: 10px;
            height: 6px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {card_bg};
            color: {text_color};
            selection-background-color: #2563EB;
            selection-color: #FFFFFF;
            border: 1px solid {border};
            border-radius: 6px;
            padding: 4px;
            outline: 0px;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 24px;
            padding: 2px 8px;
            color: {text_color};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {btn_sec_hover};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: #2563EB;
            color: #FFFFFF;
        }}
        QCheckBox {{
            font-size: 12px;
            color: {subtext_color};
            spacing: 6px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {input_border};
            border-radius: 3px;
            background-color: {input_bg};
        }}
        QCheckBox::indicator:checked {{
            background-color: #2563EB;
            border: 1px solid #2563EB;
        }}
        QPushButton {{
            font-size: 13px;
            font-weight: bold;
            border-radius: 6px;
            padding: 8px 18px;
        }}
        QPushButton#btn_primary {{
            background-color: #2563EB;
            color: #FFFFFF;
            border: none;
        }}
        QPushButton#btn_primary:hover {{
            background-color: #1D4ED8;
        }}
        QPushButton#btn_primary:disabled {{
            background-color: {'#334155' if is_dark else '#94A3B8'};
            color: {'#64748B' if is_dark else '#CBD5E1'};
        }}
        QPushButton#btn_success {{
            background-color: #16A34A;
            color: #FFFFFF;
            border: none;
        }}
        QPushButton#btn_success:hover {{
            background-color: #15803D;
        }}
        QPushButton#btn_success:disabled {{
            background-color: {'#334155' if is_dark else '#E2E8F0'};
            color: {'#64748B' if is_dark else '#94A3B8'};
        }}
        QPushButton#btn_secondary {{
            background-color: {btn_sec_bg};
            color: {subtext_color};
            border: 1px solid {input_border};
        }}
        QPushButton#btn_secondary:hover {{
            background-color: {btn_sec_hover};
            color: {text_color};
            border-color: #94A3B8;
        }}
        QPushButton#btn_mini {{
            padding: 3px 5px;
            font-size: 12px;
            font-weight: bold;
            background-color: {btn_sec_bg};
            color: #2563EB;
            border: 1px solid {input_border};
            border-radius: 4px;
        }}
        QPushButton#btn_mini:hover {{
            background-color: {btn_sec_hover};
            border-color: #2563EB;
            color: #1D4ED8;
        }}
        QPushButton#btn_settings {{
            background-color: {rule_bg};
            color: {rule_text};
            border: 1px solid {rule_border};
            border-radius: 6px;
            padding: 5px 14px;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton#btn_settings:hover {{
            background-color: {'#334155' if is_dark else '#DBEAFE'};
            color: {'#93C5FD' if is_dark else '#1D4ED8'};
        }}
        QPushButton#btn_awake_toggle {{
            background-color: {rule_bg};
            color: {rule_text};
            border: 1px solid {rule_border};
            border-radius: 6px;
            padding: 5px 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton#btn_awake_toggle:hover {{
            background-color: {'#334155' if is_dark else '#DBEAFE'};
            color: {'#93C5FD' if is_dark else '#1D4ED8'};
        }}
        QPushButton#btn_awake_toggle[active="true"] {{
            background-color: #16A34A;
            color: #FFFFFF;
            border: 1px solid #15803D;
        }}
        QPushButton#btn_awake_toggle[active="true"]:hover {{
            background-color: #15803D;
        }}
        QPushButton#btn_view_switch {{
            background-color: {btn_sec_bg};
            color: {subtext_color};
            border: 1px solid {input_border};
            border-radius: 6px;
            padding: 5px 14px;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton#btn_view_switch:hover {{
            background-color: {btn_sec_hover};
            color: {text_color};
        }}
        QPushButton#btn_view_switch:checked {{
            background-color: #2563EB;
            color: #FFFFFF;
            border: 1px solid #2563EB;
        }}
        QTableWidget {{
            background-color: {card_bg};
            alternate-background-color: {'#172033' if is_dark else '#F8FAFC'};
            border: 1px solid {border};
            border-radius: 8px;
            gridline-color: {grid_color};
            font-size: 12px;
            color: {text_color};
            selection-background-color: #2563EB;
            selection-color: #FFFFFF;
        }}
        QTableWidget::item {{
            color: {text_color};
        }}
        QHeaderView {{
            background-color: transparent;
            border: none;
        }}
        QHeaderView::section {{
            background-color: {th_bg};
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 4px;
            border: none;
            margin: 2px 2px;
            border-radius: 4px;
            font-size: 12px;
        }}
        QHeaderView::section:hover {{
            background-color: {'#334155' if is_dark else '#2D3748'};
        }}
        QProgressBar {{
            border: 1px solid {border};
            border-radius: 6px;
            text-align: center;
            height: 18px;
            background-color: {input_bg};
            color: {text_color};
            font-size: 11px;
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #FF2A54,
                stop:0.17 #FF8000,
                stop:0.34 #FFD000,
                stop:0.51 #05D550,
                stop:0.68 #00C2FF,
                stop:0.85 #4F46E5,
                stop:1.0 #A855F7);
            border-radius: 5px;
        }}
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {input_border};
            min-height: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: #94A3B8;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 8px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {input_border};
            min-width: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: #94A3B8;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
            background: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
    """


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.records: List[Dict[str, Any]] = []
        self.current_emp_name = "员工"
        self.worker_thread: Optional[ScraperThread] = None
        self._tray_notified = False

        # 初始化 Awake 屏幕常亮防休眠管理器
        self.awake_mgr = AwakeManager.get_instance()
        self.awake_mgr.state_changed.connect(self.on_awake_state_changed)
        self.awake_mgr.expired.connect(self.on_awake_expired)
        
        self.init_ui()
        self.init_tray()
        self.load_saved_config()
        self.apply_new_settings(self.config)

    def init_ui(self):
        # 界面窗口标题设为 不加了
        self.setWindowTitle("不加了")
        self.resize(1220, 860)
        self.setMinimumSize(1000, 720)
        
        # 窗口图标 (基于程序自身位置解析，不依赖当前工作目录)
        for name in ["猫咪.png", "icon.ico"]:
            ic = resource_path("img", name)
            if os.path.exists(ic):
                self.setWindowIcon(QIcon(ic))
                break

        # 中心部件采用支持背景/遮罩渲染的 BackgroundCentralWidget
        self.central_widget = BackgroundCentralWidget()
        self.central_widget.setObjectName("central_widget")
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # 1. 顶部核算规则说明 与 右侧设置按钮 (对应红框位置)
        header_layout = QHBoxLayout()
        rule_tip_short = "核算规则：周内18:00起算(0.5h颗粒度/最晚02:00) | 周末以审批单为准 | 法定节假日(节)不计入加班"
        rule_tip_full = "核算规则：周内18:00后30分钟起算(0.5h颗粒度)，最晚计至次日02:00 | 周末以审批加班单有效时长计算 | 法定节假日(节)不计入加班"
        self.rule_tip = QLabel(rule_tip_short)
        self.rule_tip.setObjectName("rule_tip")
        self.rule_tip.setToolTip(rule_tip_full)

        # 屏幕常亮快速开关徽标
        self.btn_awake_toggle = QPushButton("☕ 防息屏: 关")
        self.btn_awake_toggle.setObjectName("btn_awake_toggle")
        self.btn_awake_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_awake_toggle.setToolTip("点击快速开启/关闭屏幕常亮防休眠")
        self.btn_awake_toggle.clicked.connect(self.toggle_awake_quick)
        
        self.btn_settings = QPushButton("⚙️ 设置 (Settings)")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setToolTip("打开首选项设置 (外观、透明度、遮罩、防息屏、托盘行为、路径等)")
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        
        header_layout.addWidget(self.rule_tip)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_awake_toggle)
        header_layout.addWidget(self.btn_settings)
        main_layout.addLayout(header_layout)

        # 2. 基础信息与查询配置卡片
        input_box = QGroupBox("基础信息与查询配置")
        input_layout = QGridLayout(input_box)
        input_layout.setHorizontalSpacing(16)
        input_layout.setVerticalSpacing(10)

        # 账号 (工号)
        lbl_acc = QLabel("账号（工号）:")
        lbl_acc.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        input_layout.addWidget(lbl_acc, 0, 0)
        
        self.input_emp_id = QLineEdit()
        self.input_emp_id.setPlaceholderText("请输入工号")
        self.input_emp_id.setMinimumWidth(150)
        self.input_emp_id.textChanged.connect(self.on_emp_id_changed)
        input_layout.addWidget(self.input_emp_id, 0, 1)

        # 密码
        lbl_pwd = QLabel("登录密码:")
        lbl_pwd.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        input_layout.addWidget(lbl_pwd, 0, 2)
        
        pwd_box = QHBoxLayout()
        pwd_box.setSpacing(6)
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.setPlaceholderText("请输入 Portal 登录密码")
        self.input_password.textChanged.connect(self.on_password_changed)
        self.btn_toggle_pwd = QPushButton("显示")
        self.btn_toggle_pwd.setObjectName("btn_mini")
        self.btn_toggle_pwd.setFixedWidth(58)
        self.btn_toggle_pwd.clicked.connect(self.toggle_password_echo)
        pwd_box.addWidget(self.input_password)
        pwd_box.addWidget(self.btn_toggle_pwd)
        input_layout.addLayout(pwd_box, 0, 3)

        # 查询月份
        lbl_month = QLabel("查询月份:")
        lbl_month.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        input_layout.addWidget(lbl_month, 0, 4)
        
        date_box = QHBoxLayout()
        date_box.setSpacing(6)
        now = datetime.now()
        
        self.spin_year = QSpinBox()
        self.spin_year.setRange(2020, 2035)
        self.spin_year.setValue(now.year)
        self.spin_year.setFixedWidth(95)

        self.combo_month = QComboBox()
        self.combo_month.setMaxVisibleItems(12)
        self.combo_month.view().setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for m in range(1, 13):
            self.combo_month.addItem(f"{m:02d}月", m)
        self.combo_month.setCurrentIndex(now.month - 1)
        self.combo_month.setFixedWidth(78)
        popup_container = self.combo_month.view().parentWidget()
        if popup_container:
            popup_container.setAttribute(Qt.WA_TranslucentBackground, True)
            popup_container.setWindowFlags(popup_container.windowFlags() | Qt.FramelessWindowHint)

        btn_this_month = QPushButton("本月")
        btn_this_month.setObjectName("btn_mini")
        btn_this_month.setFixedWidth(58)
        btn_this_month.clicked.connect(self.select_this_month)
        
        btn_last_month = QPushButton("上月")
        btn_last_month.setObjectName("btn_mini")
        btn_last_month.setFixedWidth(58)
        btn_last_month.clicked.connect(self.select_last_month)
        
        date_box.addWidget(self.spin_year)
        date_box.addWidget(self.combo_month)
        date_box.addWidget(btn_this_month)
        date_box.addWidget(btn_last_month)
        input_layout.addLayout(date_box, 0, 5)

        # 选项：记住工号、记住密码
        opt_box = QHBoxLayout()
        opt_box.setSpacing(16)
        self.chk_remember_id = QCheckBox("记住工号")
        self.chk_remember_pwd = QCheckBox("记住密码")
        opt_box.addWidget(self.chk_remember_id)
        opt_box.addWidget(self.chk_remember_pwd)
        opt_box.addStretch()
        input_layout.addLayout(opt_box, 1, 1, 1, 3)

        main_layout.addWidget(input_box)

        # 3. 操作按钮与任务执行进度
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(12)
        action_layout.setAlignment(Qt.AlignVCenter)

        self.btn_start = QPushButton("▶ 开始统计")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.setFixedHeight(42)
        self.btn_start.setMinimumWidth(150)
        self.btn_start.clicked.connect(self.start_scraping)
        
        self.btn_export = QPushButton("📊 导出 Excel 报表")
        self.btn_export.setObjectName("btn_success")
        self.btn_export.setFixedHeight(42)
        self.btn_export.setMinimumWidth(150)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_excel)
        
        # 演示数据仅供调试用，默认隐藏 (config.json 的 debug_mode 或启动参数 --debug 开启)
        self.btn_mock = QPushButton("🧪 加载演示数据")
        self.btn_mock.setObjectName("btn_secondary")
        self.btn_mock.setFixedHeight(42)
        self.btn_mock.setMinimumWidth(140)
        self.btn_mock.setToolTip("调试模式专用：不访问 HR 系统，直接生成本地演示数据")
        self.btn_mock.clicked.connect(self.load_mock_data)
        self.btn_mock.setVisible(self.is_debug_mode())

        action_layout.addWidget(self.btn_start)
        action_layout.addWidget(self.btn_export)
        action_layout.addWidget(self.btn_mock)
        action_layout.addSpacing(8)

        # 进度与状态容器 (高度精确为 42px，与左侧按钮上下绝对平齐对齐)
        prog_container = QWidget()
        prog_container.setFixedHeight(42)
        prog_box = QVBoxLayout(prog_container)
        prog_box.setContentsMargins(0, 1, 0, 1)
        prog_box.setSpacing(4)

        self.lbl_status = QLabel("就绪。输入账号密码及查询月份后，点击【开始统计】。")
        self.lbl_status.setFixedHeight(18)
        self.lbl_status.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        self.lbl_status.setStyleSheet("font-weight: bold;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setValue(0)

        prog_box.addWidget(self.lbl_status)
        prog_box.addWidget(self.progress_bar)
        action_layout.addWidget(prog_container, 1)

        main_layout.addLayout(action_layout)

        # 4. KPI 统计卡片（紧凑单行模式，消除津贴等级徽章）
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(8)
        self.card_total = self.create_kpi_card("合计加班", "0.0", "小时", "#2563EB", "#EFF6FF", "#BFDBFE")
        self.card_weekday = self.create_kpi_card("工作日加班", "0.0", "小时", "#16A34A", "#F0FDF4", "#BBF7D0")
        self.card_weekend = self.create_kpi_card("非工作日加班", "0.0", "小时", "#D97706", "#FFFBEB", "#FDE68A")
        self.card_holiday = self.create_kpi_card("法定节假日", "0.0", "小时", "#64748B", "#F8FAFC", "#E2E8F0")
        self.card_holiday.setToolTip("法定节假日(节)不计入加班时长与津贴")
        self.card_allowance = self.create_kpi_card("加班津贴", "0", "元", "#7C3AED", "#FAF5FF", "#E9D5FF")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_weekday)
        kpi_layout.addWidget(self.card_weekend)
        kpi_layout.addWidget(self.card_holiday)
        kpi_layout.addWidget(self.card_allowance)
        main_layout.addLayout(kpi_layout)

        # 5. 视图切换栏 (表格视图 vs 日历视图)
        view_switch_layout = QHBoxLayout()
        view_switch_layout.setContentsMargins(2, 4, 2, 2)
        
        self.lbl_view_title = QLabel("📌 出勤与加班数据概览")
        self.lbl_view_title.setFont(QFont("JetBrains Mono", 11, QFont.Bold))
        view_switch_layout.addWidget(self.lbl_view_title)
        view_switch_layout.addStretch()

        self.btn_view_table = QPushButton("📋 表格视图")
        self.btn_view_table.setObjectName("btn_view_switch")
        self.btn_view_table.setCheckable(True)
        self.btn_view_table.setChecked(True)
        self.btn_view_table.clicked.connect(lambda: self.switch_view(0))

        self.btn_view_calendar = QPushButton("📅 日历视图")
        self.btn_view_calendar.setObjectName("btn_view_switch")
        self.btn_view_calendar.setCheckable(True)
        self.btn_view_calendar.clicked.connect(lambda: self.switch_view(1))

        view_switch_layout.addWidget(self.btn_view_table)
        view_switch_layout.addWidget(self.btn_view_calendar)
        main_layout.addLayout(view_switch_layout)

        # 6. 堆叠视图组件
        self.view_stack = QStackedWidget()

        # 视图 0: 表格视图
        self.table = QTableWidget()
        headers = [
            "序号", "日期", "星期", 
            "上班打卡明细", "下班打卡明细", "加班时间 (小时)", 
            "考勤班次", "核算类别", "加班计算依据与备注"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 优化各列宽度，确保 1000px 默认窗口下全部 9 列直接完整显示，即使出现垂直滚动条也绝不触发底部横向滚动条
        col_widths = [45, 85, 50, 100, 100, 110, 140, 85, 160]
        for idx, w in enumerate(col_widths):
            self.table.setColumnWidth(idx, w)
        self.view_stack.addWidget(self.table)

        # 视图 1: 日历看板视图
        self.calendar_view = AttendanceCalendarWidget()
        self.view_stack.addWidget(self.calendar_view)

        main_layout.addWidget(self.view_stack, 1)

    def init_tray(self):
        """初始化系统托盘图标与上下文菜单 (含防息屏快捷子菜单)"""
        self.tray_icon = QSystemTrayIcon(self)
        for name in ["icon.ico", "猫咪.png"]:
            icon_path = resource_path("img", name)
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
                break
            
        self.tray_icon.setToolTip("不加了")

        tray_menu = QMenu()
        act_show = QAction("显示主界面", self)
        act_show.triggered.connect(self.show_and_activate)

        # 屏幕常亮防休眠快捷子菜单
        menu_awake = QMenu("屏幕常亮防休眠", self)
        self.act_awake_indefinite = QAction("持续常亮", self, checkable=True)
        self.act_awake_1h = QAction("保持 1 小时", self, checkable=True)
        self.act_awake_2h = QAction("保持 2 小时", self, checkable=True)
        self.act_awake_4h = QAction("保持 4 小时", self, checkable=True)
        self.act_awake_8h = QAction("保持 8 小时", self, checkable=True)
        self.act_awake_off = QAction("关闭防息屏", self, checkable=True)

        self.act_awake_indefinite.triggered.connect(lambda: self.set_awake_from_tray("indefinite", 0))
        self.act_awake_1h.triggered.connect(lambda: self.set_awake_from_tray("timed", 1))
        self.act_awake_2h.triggered.connect(lambda: self.set_awake_from_tray("timed", 2))
        self.act_awake_4h.triggered.connect(lambda: self.set_awake_from_tray("timed", 4))
        self.act_awake_8h.triggered.connect(lambda: self.set_awake_from_tray("timed", 8))
        self.act_awake_off.triggered.connect(lambda: self.set_awake_from_tray("off", 0))

        menu_awake.addAction(self.act_awake_indefinite)
        menu_awake.addAction(self.act_awake_1h)
        menu_awake.addAction(self.act_awake_2h)
        menu_awake.addAction(self.act_awake_4h)
        menu_awake.addAction(self.act_awake_8h)
        menu_awake.addSeparator()
        menu_awake.addAction(self.act_awake_off)

        act_settings = QAction("首选项设置", self)
        act_settings.triggered.connect(self.open_settings_dialog)
        act_quit = QAction("退出程序", self)
        act_quit.triggered.connect(self.quit_app)

        tray_menu.addAction(act_show)
        tray_menu.addMenu(menu_awake)
        tray_menu.addAction(act_settings)
        tray_menu.addSeparator()
        tray_menu.addAction(act_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        self.update_tray_awake_actions()

    def set_awake_from_tray(self, mode: str, hours: int):
        """从托盘快捷菜单设置屏幕常亮防休眠"""
        if mode == "off":
            self.awake_mgr.disable()
            self.config["awake_enabled"] = False
        else:
            self.awake_mgr.enable(mode=mode, hours=hours)
            self.config["awake_enabled"] = True
            self.config["awake_mode"] = mode
            if hours > 0:
                self.config["awake_hours"] = hours
        save_config(self.config)
        self.update_tray_awake_actions()

    def update_tray_awake_actions(self):
        """同步托盘勾选项状态"""
        if not hasattr(self, 'act_awake_indefinite'):
            return
        is_active = self.awake_mgr.is_active
        mode = self.awake_mgr.mode
        hours = self.awake_mgr.target_hours

        self.act_awake_off.setChecked(not is_active)
        self.act_awake_indefinite.setChecked(is_active and mode == "indefinite")
        self.act_awake_1h.setChecked(is_active and mode == "timed" and hours == 1)
        self.act_awake_2h.setChecked(is_active and mode == "timed" and hours == 2)
        self.act_awake_4h.setChecked(is_active and mode == "timed" and hours == 4)
        self.act_awake_8h.setChecked(is_active and mode == "timed" and hours == 8)

    def toggle_awake_quick(self):
        """主界面快速切换屏幕常亮防休眠开关"""
        if self.awake_mgr.is_active:
            self.awake_mgr.disable()
            self.config["awake_enabled"] = False
        else:
            mode = self.config.get("awake_mode", "indefinite")
            hours = int(self.config.get("awake_hours", 2))
            self.awake_mgr.enable(mode=mode, hours=hours)
            self.config["awake_enabled"] = True
        save_config(self.config)
        self.update_tray_awake_actions()

    def on_awake_state_changed(self, is_active: bool, status_text: str):
        """响应防息屏状态改变"""
        if hasattr(self, 'btn_awake_toggle'):
            if is_active:
                self.btn_awake_toggle.setProperty("active", "true")
                if self.awake_mgr.mode == "timed":
                    rem = self.awake_mgr.remaining_seconds()
                    h = rem // 3600
                    m = (rem % 3600) // 60
                    s = rem % 60
                    self.btn_awake_toggle.setText(f"☕ {h:02d}:{m:02d}:{s:02d}")
                else:
                    self.btn_awake_toggle.setText("☕ 常亮中")
                self.btn_awake_toggle.setToolTip(f"防息屏状态: {status_text} (点击快速关闭)")
            else:
                self.btn_awake_toggle.setProperty("active", "false")
                self.btn_awake_toggle.setText("☕ 防息屏: 关")
                self.btn_awake_toggle.setToolTip("防息屏已关闭 (点击快速开启)")

            self.btn_awake_toggle.style().unpolish(self.btn_awake_toggle)
            self.btn_awake_toggle.style().polish(self.btn_awake_toggle)

        if hasattr(self, 'tray_icon'):
            self.tray_icon.setToolTip(f"不加了\n☕ 状态: {status_text}")
            self.update_tray_awake_actions()

    def on_awake_expired(self):
        """倒计时结束时轻量提示"""
        if hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage(
                "不加了",
                "屏幕防息屏倒计时已结束，系统已恢复正常电源休眠策略。",
                QSystemTrayIcon.Information,
                3000
            )
        self.config["awake_enabled"] = False
        save_config(self.config)
        self.update_tray_awake_actions()

    def notify_started_in_tray(self):
        """静默启动到托盘时给出气泡提示，避免用户误以为程序没启动"""
        if hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage(
                "不加了",
                "已在系统托盘静默启动，双击托盘图标可打开主界面。",
                QSystemTrayIcon.Information,
                2500
            )
            self._tray_notified = True

    def show_and_activate(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
        self.raise_()

    def on_tray_activated(self, reason):
        if reason in [QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger]:
            if self.isVisible():
                if self.isMinimized():
                    self.showNormal()
                self.activateWindow()
            else:
                self.show_and_activate()

    def open_settings_dialog(self):
        dlg = SettingsDialog(self.config, self)
        dlg.settings_changed.connect(self.apply_new_settings)
        if dlg.exec_() == QDialog.Accepted:
            new_settings = dlg.get_current_settings()
            self.apply_new_settings(new_settings)
            self.config.update(new_settings)
            save_config(self.config)

    def apply_new_settings(self, settings: dict):
        """即时应用外观、背景、透明度、遮罩、模糊度、防息屏与主题样式"""
        # 1. 窗口整体透明度
        op = int(settings.get("window_opacity", 100))
        self.setWindowOpacity(max(0.3, min(1.0, op / 100.0)))

        # 2. 背景与模糊度渲染
        theme = settings.get("theme", "light")
        is_dark = (theme == "dark")
        bg_path = settings.get("bg_image_path", "").strip()
        mask_density = int(settings.get("mask_density", 20))
        blur_radius = int(settings.get("blur_radius", 0))

        pixmap = load_and_process_bg(bg_path, blur_radius)
        has_bg = (pixmap is not None)
        self.central_widget.set_background(pixmap, mask_density, is_dark=is_dark)

        # 3. 样式表更新
        qss = get_app_stylesheet(is_dark=is_dark, has_bg=has_bg)
        self.setStyleSheet(qss)

        # 3.1 combo_month 下拉列表弹窗专属主题着色与无白边处理
        if hasattr(self, 'combo_month'):
            popup_card_bg = "#1E293B" if is_dark else "#FFFFFF"
            popup_border = "#334155" if is_dark else "#CBD5E1"
            popup_text = "#F8FAFC" if is_dark else "#0F172A"
            popup_hover = "#334155" if is_dark else "#F1F5F9"
            combo_view_qss = f"""
                QAbstractItemView {{
                    background-color: {popup_card_bg};
                    color: {popup_text};
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                    border: 1px solid {popup_border};
                    border-radius: 6px;
                    padding: 4px;
                    outline: 0px;
                }}
                QAbstractItemView::item {{
                    min-height: 24px;
                    padding: 2px 8px;
                    color: {popup_text};
                }}
                QAbstractItemView::item:hover {{
                    background-color: {popup_hover};
                }}
                QAbstractItemView::item:selected {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
            """
            self.combo_month.view().setStyleSheet(combo_view_qss)
            popup_container = self.combo_month.view().parentWidget()
            if popup_container:
                popup_container.setAttribute(Qt.WA_TranslucentBackground, True)
                popup_container.setWindowFlags(popup_container.windowFlags() | Qt.FramelessWindowHint)
                p = popup_container.palette()
                p.setColor(popup_container.backgroundRole(), QColor(popup_card_bg))
                popup_container.setPalette(p)

        # 4. 标题与状态文字颜色
        if hasattr(self, 'lbl_view_title'):
            self.lbl_view_title.setStyleSheet(f"color: {'#F8FAFC' if is_dark else '#0F172A'};")
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setStyleSheet(f"font-weight: bold; color: {'#94A3B8' if is_dark else '#1E293B'};")

        # 5. 更新 KPI 卡片色彩
        self.update_kpi_cards_theme(is_dark)

        # 6. 更新日历看板模式
        if hasattr(self, 'calendar_view'):
            self.calendar_view.set_dark_mode(is_dark)

        # 7. 屏幕常亮防休眠设置
        awake_en = bool(settings.get("awake_enabled", False))
        if awake_en:
            self.awake_mgr.enable(
                mode=settings.get("awake_mode", "indefinite"),
                hours=int(settings.get("awake_hours", 2))
            )
        else:
            self.awake_mgr.disable()

        # 8. 开机自启 与 启动后隐藏到托盘 (两项独立)
        if "autostart" in settings:
            from utils.autostart_mgr import set_autostart
            set_autostart(
                bool(settings["autostart"]),
                bool(settings.get("start_minimized", self.config.get("start_minimized", False)))
            )

        # 9. 调试模式：控制演示数据按钮可见性
        if hasattr(self, 'btn_mock'):
            self.btn_mock.setVisible(self.is_debug_mode(settings))

        # 10. 垂直滚动条显示与隐藏 (个性化配置)
        show_sb = bool(settings.get("show_scrollbar", False))
        v_policy = Qt.ScrollBarAsNeeded if show_sb else Qt.ScrollBarAlwaysOff
        if hasattr(self, 'table'):
            self.table.setVerticalScrollBarPolicy(v_policy)
        if hasattr(self, 'calendar_view') and hasattr(self.calendar_view, 'scroll'):
            self.calendar_view.scroll.setVerticalScrollBarPolicy(v_policy)

    def update_kpi_cards_theme(self, is_dark: bool):
        card_configs = [
            (self.card_total, "#2563EB" if not is_dark else "#60A5FA", "#EFF6FF" if not is_dark else "#1E293B", "#BFDBFE" if not is_dark else "#2563EB"),
            (self.card_weekday, "#16A34A" if not is_dark else "#4ADE80", "#F0FDF4" if not is_dark else "#1E293B", "#BBF7D0" if not is_dark else "#15803D"),
            (self.card_weekend, "#D97706" if not is_dark else "#FBBF24", "#FFFBEB" if not is_dark else "#1E293B", "#FDE68A" if not is_dark else "#B45309"),
            (self.card_holiday, "#64748B" if not is_dark else "#94A3B8", "#F8FAFC" if not is_dark else "#1E293B", "#E2E8F0" if not is_dark else "#475569"),
            (self.card_allowance, "#7C3AED" if not is_dark else "#C084FC", "#FAF5FF" if not is_dark else "#1E293B", "#E9D5FF" if not is_dark else "#7E22CE"),
        ]
        for card, text_c, bg_c, border_c in card_configs:
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_c};
                    border: 1px solid {border_c};
                    border-radius: 6px;
                }}
            """)
            card.lbl_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {text_c}; font-family: 'JetBrains Mono', Consolas, monospace;")
            card.lbl_title.setStyleSheet(f"font-size: 11px; color: {'#CBD5E1' if is_dark else '#475569'}; font-weight: bold;")
            card.lbl_unit.setStyleSheet(f"font-size: 10px; color: {'#94A3B8' if is_dark else '#64748B'};")
            if hasattr(card, 'lbl_sub'):
                card.lbl_sub.setVisible(False)

    def is_debug_mode(self, settings: Optional[dict] = None) -> bool:
        """调试模式开关：首选项中的 debug_mode，或启动参数 --debug"""
        cfg = settings if settings is not None else self.config
        return bool(cfg.get("debug_mode", False)) or "--debug" in sys.argv

    def switch_view(self, index: int):
        self.view_stack.setCurrentIndex(index)
        if index == 0:
            self.btn_view_table.setChecked(True)
            self.btn_view_calendar.setChecked(False)
        else:
            self.btn_view_table.setChecked(False)
            self.btn_view_calendar.setChecked(True)

    def create_kpi_card(self, title: str, val: str, unit: str, text_color: str, bg_color: str, border_color: str) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11px; color: #475569; font-weight: bold;")
        
        lbl_val = QLabel(val)
        lbl_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {text_color}; font-family: 'JetBrains Mono', Consolas, monospace;")
        
        lbl_unit = QLabel(unit)
        lbl_unit.setStyleSheet("font-size: 10px; color: #64748B;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_unit)
        
        frame.lbl_title = lbl_title
        frame.lbl_val = lbl_val
        frame.lbl_unit = lbl_unit
        return frame

    def toggle_password_echo(self):
        if self.input_password.echoMode() == QLineEdit.Password:
            self.input_password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_pwd.setText("隐藏")
        else:
            self.input_password.setEchoMode(QLineEdit.Password)
            self.btn_toggle_pwd.setText("显示")

    def select_this_month(self):
        now = datetime.now()
        self.spin_year.setValue(now.year)
        self.combo_month.setCurrentIndex(now.month - 1)

    def select_last_month(self):
        now = datetime.now()
        if now.month == 1:
            self.spin_year.setValue(now.year - 1)
            self.combo_month.setCurrentIndex(11)
        else:
            self.spin_year.setValue(now.year)
            self.combo_month.setCurrentIndex(now.month - 2)

    def load_saved_config(self):
        cfg = self.config
        if cfg.get("remember_emp_id"):
            self.input_emp_id.setText(cfg.get("emp_id", ""))
            self.chk_remember_id.setChecked(True)
        if cfg.get("remember_password"):
            self.input_password.setText(get_saved_password(cfg))
            self.chk_remember_pwd.setChecked(True)
        if cfg.get("awake_enabled", False):
            self.awake_mgr.enable(
                mode=cfg.get("awake_mode", "indefinite"),
                hours=int(cfg.get("awake_hours", 2))
            )
        # 勾选变化时立即自动落盘保存 (C1)
        self.chk_remember_id.toggled.connect(self.save_current_config)
        self.chk_remember_pwd.toggled.connect(self.save_current_config)

    def save_current_config(self):
        remember_id = self.chk_remember_id.isChecked()
        remember_pwd = self.chk_remember_pwd.isChecked()
        self.config["remember_emp_id"] = remember_id
        self.config["remember_password"] = remember_pwd
        self.config["emp_id"] = self.input_emp_id.text().strip() if remember_id else ""
        # 密码禁止空格，并经 Windows DPAPI 加密后落盘
        clean_pwd = self.input_password.text().replace(" ", "") if remember_pwd else ""
        set_saved_password(self.config, clean_pwd)
        save_config(self.config)

    def start_scraping(self):
        emp_id = self.input_emp_id.text().strip()
        # 严格禁止密码包含任何空格
        password = self.input_password.text().replace(" ", "")
        year = self.spin_year.value()
        month = self.combo_month.currentData()

        if not emp_id:
            StyledMessageBox.warning(self, "提示", "请输入账号", "请输入员工账号（工号）！")
            self.input_emp_id.setFocus()
            return
        if not password:
            StyledMessageBox.warning(self, "提示", "请输入密码", "请输入 Portal 登录密码！")
            self.input_password.setFocus()
            return

        self.save_current_config()
        self.btn_start.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Loading...")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #2563EB;")

        rules = {
            "weekday_end": self.config.get("weekday_end", "17:30"),
            "weekday_ot_start": self.config.get("weekday_ot_start", "18:00"),
            "ot_latest_end": self.config.get("ot_latest_end", "02:00"),
            "min_ot_minutes": self.config.get("min_ot_minutes", 30),
            "granularity_minutes": self.config.get("granularity_minutes", 30),
            "include_weekend_base": self.config.get("include_weekend_base", True)
        }

        # 始终保持后台静默无头模式，优先使用配置中保存的 Edge 路径
        edge_path = self.config.get("edge_path", "")
        self.worker_thread = ScraperThread(emp_id, password, year, month, rules, headless=True, edge_path=edge_path)
        self.worker_thread.log_signal.connect(self.on_worker_progress)
        self.worker_thread.finished_signal.connect(self.on_worker_finished)
        self.worker_thread.start()

    def on_worker_progress(self, msg: str, pct: int):
        if any(k in msg for k in ["驱动", "WebDriver", "下载", "配置"]):
            self.lbl_status.setText(msg)
            self.lbl_status.setStyleSheet("font-weight: bold; color: #0284C7;")
            self.progress_bar.setValue(pct)
            return

        if 0 <= pct < 100:
            # 统一显示 Loading...，不显示具体日期等读取细节
            self.lbl_status.setText("Loading...")
            self.lbl_status.setStyleSheet("font-weight: bold; color: #2563EB;")
        else:
            self.lbl_status.setText(msg)
            is_dark = (self.config.get("theme", "light") == "dark")
            self.lbl_status.setStyleSheet(f"font-weight: bold; color: {'#94A3B8' if is_dark else '#1E293B'};")
        self.progress_bar.setValue(pct)

    def on_password_changed(self):
        curr = self.input_password.text()
        if " " in curr:
            # 自动过滤密码中的空格
            clean = curr.replace(" ", "")
            pos = self.input_password.cursorPosition()
            self.input_password.blockSignals(True)
            self.input_password.setText(clean)
            self.input_password.setCursorPosition(max(0, pos - 1))
            self.input_password.blockSignals(False)
        if self.chk_remember_pwd.isChecked():
            self.save_current_config()

    def on_emp_id_changed(self):
        if self.chk_remember_id.isChecked():
            self.save_current_config()

    def on_worker_finished(self, success: bool, emp_name: str, error_msg: str, records: list, failed_days: list = None):
        self.btn_start.setEnabled(True)
        is_dark = (self.config.get("theme", "light") == "dark")

        if success:
            self.current_emp_name = emp_name
            self.records = records
            self.update_table_and_kpis(records)
            self.btn_export.setEnabled(True)
            if failed_days:
                self.lbl_status.setText(f"核算完成！注意：有 {len(failed_days)} 天打卡读取超时（{', '.join(failed_days)}），已在表格/报表中进行标注。")
                self.lbl_status.setStyleSheet("font-weight: bold; color: #D97706;")
                StyledMessageBox.warning(
                    self,
                    "打卡读取提示",
                    f"有 {len(failed_days)} 天打卡详情未能从 HR 系统读取完整",
                    f"涉及日期: {', '.join(failed_days)}\n系统已在对应日期备注中标注，建议稍后重试或在系统手工核对！"
                )
            else:
                self.lbl_status.setText(f"核算完成！当月共 {len(records)} 天上下班明细已全部更新。")
                self.lbl_status.setStyleSheet("font-weight: bold; color: #16A34A;")
            self.progress_bar.setValue(100)
        else:
            self.lbl_status.setText("统计失败。请检查账号、密码或网络状态。")
            self.lbl_status.setStyleSheet("font-weight: bold; color: #DC2626;")
            self.progress_bar.setValue(0)
            
            if "用户名或密码错误" in error_msg or "密码" in error_msg or "login" in error_msg.lower():
                StyledMessageBox.warning(
                    self, 
                    "登录认证失败", 
                    "工号或密码输入错误",
                    f"系统返回提示：{error_msg}\n\n请仔细核对您输入的工号和 Portal 密码后重试！"
                )
            else:
                StyledMessageBox.critical(
                    self, 
                    "统计执行失败", 
                    "自动化采集过程遇到异常",
                    f"错误详情：\n{error_msg}"
                )

    def update_table_and_kpis(self, records: List[Dict[str, Any]]):
        self.table.setRowCount(0)
        total_ot = 0.0
        weekday_ot = 0.0
        weekend_ot = 0.0
        holiday_ot = 0.0

        is_dark = (self.config.get("theme", "light") == "dark")

        for idx, r in enumerate(records):
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)

            ot = float(r.get("overtime_hours", 0.0))
            detail_type = r.get("detail_type", "正常工时")

            if detail_type in ["周内加班", "工作日加班"]:
                weekday_ot += ot
                total_ot += ot
            elif detail_type == "周末加班":
                weekend_ot += ot
                total_ot += ot
            elif detail_type == "法定节假日":
                holiday_ot += float(r.get("declared_ot_hours", ot))

            items = [
                QTableWidgetItem(str(r.get("seq", idx + 1))),
                QTableWidgetItem(r.get("date", "")),
                QTableWidgetItem(r.get("weekday", "")),
                QTableWidgetItem(r.get("check_in", "-")),
                QTableWidgetItem(r.get("check_out", "-")),
                QTableWidgetItem(f"{ot:.1f} 小时" if ot > 0 else "0.0 小时"),
                QTableWidgetItem(r.get("shift_name", "")),
                QTableWidgetItem(detail_type),
                QTableWidgetItem(r.get("notes", ""))
            ]

            # 居中对齐前 6 列
            for i in range(6):
                items[i].setTextAlignment(Qt.AlignCenter)
            items[6].setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            items[7].setTextAlignment(Qt.AlignCenter)
            items[8].setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            # 高亮突出加班数据
            if ot > 0:
                font = QFont("JetBrains Mono", 10, QFont.Bold)
                items[5].setFont(font)
                if detail_type in ["周内加班", "工作日加班"]:
                    items[5].setForeground(QColor("#16A34A" if not is_dark else "#4ADE80"))
                elif detail_type == "周末加班":
                    items[5].setForeground(QColor("#D97706" if not is_dark else "#FBBF24"))
                elif detail_type == "法定节假日":
                    items[5].setForeground(QColor("#EF4444" if not is_dark else "#F87171"))
            # 设置普通列前景色
            item_text_color = QColor("#F8FAFC" if is_dark else "#0F172A")
            for c_idx in [0, 1, 2, 3, 4, 6, 7, 8]:
                items[c_idx].setForeground(item_text_color)

            for col_idx, item in enumerate(items):
                self.table.setItem(row_pos, col_idx, item)

        # 更新 KPI 卡片
        self.card_total.lbl_val.setText(f"{total_ot:.1f}")
        self.card_weekday.lbl_val.setText(f"{weekday_ot:.1f}")
        self.card_weekend.lbl_val.setText(f"{weekend_ot:.1f}")
        self.card_holiday.lbl_val.setText(f"{holiday_ot:.1f}")

        # 计算加班津贴
        allowance, level_name, tier_desc = calculate_overtime_allowance(total_ot)

        self.card_allowance.lbl_val.setText(str(allowance))
        if hasattr(self.card_allowance, 'lbl_sub'):
            self.card_allowance.lbl_sub.setText(level_name)
        self.card_allowance.setToolTip(f"月累计加班时长: {total_ot:.1f} 小时\n对应津贴等级: {level_name} ({tier_desc})\n月度应发加班津贴: {allowance} 元")

        # 同步更新日历看板
        year = self.spin_year.value()
        month = self.combo_month.currentData()
        self.calendar_view.update_calendar(year, month, records)

    def export_excel(self):
        if not self.records:
            StyledMessageBox.warning(self, "提示", "暂无可导出的数据", "请先执行统计或加载数据！")
            return
        year = self.spin_year.value()
        month = self.combo_month.currentData()
        emp_id = self.input_emp_id.text().strip()
        default_filename = f"加班时长统计_{self.current_emp_name}_{emp_id}_{year}年{month:02d}月.xlsx"

        # 优先采用用户手动设置的自定义默认路径
        custom_dir = self.config.get("custom_export_path", "").strip()
        if custom_dir:
            try:
                os.makedirs(custom_dir, exist_ok=True)
                init_path = os.path.join(custom_dir, default_filename)
            except Exception:
                init_path = default_filename
        else:
            init_path = default_filename

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出加班时长统计报表", init_path, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            import calendar
            _, last_day = calendar.monthrange(year, month)
            date_range_str = f"{year}年{month:02d}月01日 至 {year}年{month:02d}月{last_day:02d}日"
            export_overtime_to_excel(
                records=self.records,
                emp_id=emp_id,
                emp_name=self.current_emp_name,
                date_range_str=date_range_str,
                output_path=file_path
            )
            StyledMessageBox.information(self, "导出成功", "报表已成功导出", f"文件保存路径:\n{file_path}")
        except Exception as e:
            StyledMessageBox.critical(self, "导出失败", "导出过程中发生错误", str(e))

    def load_mock_data(self, quiet: bool = False):
        """根据用户实际系统考勤数据载入演示数据"""
        from datetime import date
        from core.calculator import calculate_daily_overtime
        year = self.spin_year.value()
        month = self.combo_month.currentData()
        import calendar
        _, last_day = calendar.monthrange(year, month)
        
        mock_records = []
        for d in range(1, last_day + 1):
            cur_date = date(year, month, d)
            w = cur_date.weekday()
            
            if month == 5 and d in [1, 2, 3, 4, 5]:
                shift = "SD3-职员公休白班 (08:30-17:30)"
                cin = "05-01 08:12" if d == 1 else "-"
                cout = "05-01 20:33" if d == 1 else "-"
            elif w in [5, 6]:
                shift = "SD3-职员公休"
                cin = "-"
                cout = "-"
            else:
                shift = "SD3-职员白班 (08:30-17:30)"
                cin = f"{month:02d}-{d:02d} 08:15"
                if d == 1:
                    cout = f"{month:02d}-{d:02d} 21:31"  # 加班 3.5h
                elif d == 7:
                    cout = f"{month:02d}-{d:02d} 20:31"  # 加班 2.5h
                elif d % 3 == 0:
                    cout = f"{month:02d}-{d:02d} 21:00"  # 加班 3.0h
                elif d % 5 == 0:
                    cout = f"{month:02d}-{d:02d} 19:30"  # 加班 1.5h
                else:
                    cout = f"{month:02d}-{d:02d} 17:40"  # 正常下班无加班
                    
            r = calculate_daily_overtime(
                record_date=cur_date,
                shift_name=shift,
                check_in_str=cin,
                check_out_str=cout
            )
            mock_records.append(r)
            
        self.current_emp_name = self.input_emp_id.text().strip() or "示例员工"
        self.records = mock_records
        self.update_table_and_kpis(mock_records)
        self.btn_export.setEnabled(True)
        if not quiet:
            self.lbl_status.setText(f"已生成 {year}年{month:02d}月 明细数据！随时可点击【导出 Excel】。")
            self.progress_bar.setValue(100)

    def quit_app(self):
        """完全退出应用程序并释放所有后台、浏览器与电源策略资源"""
        if hasattr(self, 'awake_mgr'):
            self.awake_mgr.cleanup()
        if self.worker_thread and self.worker_thread.isRunning():
            if self.worker_thread.cdp_mgr:
                try:
                    self.worker_thread.cdp_mgr.quit()
                except Exception:
                    pass
            self.worker_thread.terminate()
            self.worker_thread.wait(1500)
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        self.save_current_config()
        QApplication.quit()

    def closeEvent(self, event):
        """根据用户首选项配置决定关闭窗口行为 (1. 隐藏到托盘 / 2. 直接退出)"""
        # 关闭窗口前确保当前配置已自动持久化落盘 (C1)
        self.save_current_config()
        close_action = self.config.get("close_action", "tray")
        if close_action == "tray":
            event.ignore()
            self.hide()
            if not self._tray_notified:
                self.tray_icon.showMessage(
                    "不加了",
                    "程序已最小化至系统托盘，双击托盘图标可重新打开。",
                    QSystemTrayIcon.Information,
                    2000
                )
                self._tray_notified = True
        else:
            self.quit_app()
            event.accept()
