import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QButtonGroup, QSlider,
    QFileDialog, QWidget, QFrame, QCheckBox, QSpinBox,
    QTabWidget, QTabBar, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

from core.awake_mgr import AwakeManager
from utils.autostart_mgr import is_autostart_enabled, set_autostart
from utils.paths import resource_path
from gui.styled_dialog import StyledMessageBox


class SettingsDialog(QDialog):
    """
    首选项设置窗口：分为三个清晰栏目（选项卡/栏目）：
    1. 🎨 外观与个性化 (Appearance)
    2. ☕ 屏幕常亮防休眠 (Awake)
    3. ⚙️ 常规与行为 (General & Behavior) - 含开机自启与静默托盘
    """
    settings_changed = pyqtSignal(dict)  # 发射变更后的最新设置字典

    def __init__(self, current_config: dict, parent=None):
        super().__init__(parent)
        self.config = current_config.copy()
        self.original_config = current_config.copy()
        self._edge_click_count = 0
        self._edge_widgets = []  # 隐藏的 Edge 路径相关控件
        
        self.init_ui()
        self.load_values()

    def init_ui(self):
        self.setWindowTitle("首选项设置 - 不加了")
        self.resize(620, 500)
        self.setMinimumSize(560, 420)
        
        # 窗口图标
        for name in ["icon.ico", "猫咪.png"]:
            p = resource_path("img", name)
            if os.path.exists(p):
                self.setWindowIcon(QIcon(p))
                break

        # 统一 JetBrains Mono 风格
        is_dark = self.config.get("theme", "light") == "dark"
        self.apply_dialog_style(is_dark)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        # 标题栏简述
        title_box = QHBoxLayout()
        self.lbl_title = QLabel("⚙️ 首选项设置 / Preferences")
        self.lbl_title.setFont(QFont("JetBrains Mono", 14, QFont.Bold))
        self.lbl_title.setCursor(Qt.PointingHandCursor)
        self.lbl_title.mousePressEvent = self._on_title_clicked
        title_box.addWidget(self.lbl_title)
        title_box.addStretch()
        main_layout.addLayout(title_box)

        # ----------------------------------------------------
        # 核心：直接分为三栏目 (QTabWidget)
        # ----------------------------------------------------
        self.tab_widget = QTabWidget()
        # 紧凑的文档式标签栏：不再拉伸占满 (原先会在右侧留下一整块空白色块)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setUsesScrollButtons(False)
        self.tab_widget.tabBar().setExpanding(False)
        self.tab_widget.tabBar().setDrawBase(False)

        # 栏目 1: 个性化
        self.tab_widget.addTab(self._wrap_scrollable(self._create_tab_appearance()), "个性化")

        # 栏目 2: Awake
        self.tab_widget.addTab(self._wrap_scrollable(self._create_tab_awake()), "Awake")

        # 栏目 3: 启动设置
        self.tab_widget.addTab(self._wrap_scrollable(self._create_tab_behavior()), "启动设置")

        main_layout.addWidget(self.tab_widget, 1)

        # ----------------------------------------------------
        # 底部操作按钮栏
        # ----------------------------------------------------
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("取消 (Cancel)")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self._on_cancel)

        btn_apply = QPushButton("应用 (Apply)")
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.clicked.connect(self._on_apply)

        btn_ok = QPushButton("确定 (OK)")
        btn_ok.setObjectName("btn_primary")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(self._on_ok)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_apply)
        btn_box.addWidget(btn_ok)
        main_layout.addLayout(btn_box)

    def _wrap_scrollable(self, page: QWidget) -> QScrollArea:
        """
        把栏目内容放进滚动区域：窗口再矮也不会出现控件被压扁、文字重叠看不清的情况
        """
        scroll = QScrollArea()
        scroll.setObjectName("tab_scroll")
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        page.setAutoFillBackground(False)
        return scroll

    # --------------------------------------------------------
    # 栏目 1: 外观与个性化
    # --------------------------------------------------------
    def _create_tab_appearance(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(8)

        # 1. 主题风格
        lbl_theme = QLabel("界面主题风格 (Theme):")
        lbl_theme.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(lbl_theme)

        theme_layout = QHBoxLayout()
        self.radio_light = QRadioButton("☀️ 浅色主题 (Light)")
        self.radio_dark = QRadioButton("🌙 深色主题 (Dark)")
        self.btn_grp_theme = QButtonGroup(self)
        self.btn_grp_theme.addButton(self.radio_light)
        self.btn_grp_theme.addButton(self.radio_dark)
        theme_layout.addWidget(self.radio_light)
        theme_layout.addWidget(self.radio_dark)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        self.radio_light.toggled.connect(self._on_theme_changed)

        # 2. 背景图片
        lbl_bg = QLabel("自定义背景图片 (Custom Background):")
        lbl_bg.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(lbl_bg)

        bg_path_layout = QHBoxLayout()
        self.edit_bg_path = QLineEdit()
        self.edit_bg_path.setPlaceholderText("可直接键盘输入或粘贴本地图片路径 (如 D:\\Pictures\\bg.jpg)")
        btn_browse_bg = QPushButton("浏览...")
        btn_browse_bg.setCursor(Qt.PointingHandCursor)
        btn_browse_bg.clicked.connect(self._browse_bg_image)
        btn_clear_bg = QPushButton("清除背景")
        btn_clear_bg.setCursor(Qt.PointingHandCursor)
        btn_clear_bg.clicked.connect(self._clear_bg_image)

        bg_path_layout.addWidget(self.edit_bg_path, 1)
        bg_path_layout.addWidget(btn_browse_bg)
        bg_path_layout.addWidget(btn_clear_bg)
        layout.addLayout(bg_path_layout)

        # 3. 窗口整体透明度 (50% ~ 100%)
        opacity_header = QHBoxLayout()
        lbl_opacity = QLabel("窗口透明度 (Window Opacity):")
        lbl_opacity.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        self.lbl_opacity_val = QLabel("100%")
        self.lbl_opacity_val.setStyleSheet("color: #2563EB; font-weight: bold;")
        opacity_header.addWidget(lbl_opacity)
        opacity_header.addStretch()
        opacity_header.addWidget(self.lbl_opacity_val)
        layout.addLayout(opacity_header)

        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(50, 100)
        self.slider_opacity.setValue(100)
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider)
        layout.addWidget(self.slider_opacity)

        # 4. 背景遮罩浓度 (0% ~ 90%)
        mask_header = QHBoxLayout()
        lbl_mask = QLabel("背景遮罩浓度 (Mask Density):")
        lbl_mask.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        self.lbl_mask_val = QLabel("20%")
        self.lbl_mask_val.setStyleSheet("color: #2563EB; font-weight: bold;")
        mask_header.addWidget(lbl_mask)
        mask_header.addStretch()
        mask_header.addWidget(self.lbl_mask_val)
        layout.addLayout(mask_header)

        self.slider_mask = QSlider(Qt.Horizontal)
        self.slider_mask.setRange(0, 90)
        self.slider_mask.setValue(20)
        self.slider_mask.valueChanged.connect(self._on_mask_slider)
        layout.addWidget(self.slider_mask)

        # 5. 毛玻璃模糊度 (0 ~ 30 px)
        blur_header = QHBoxLayout()
        lbl_blur = QLabel("毛玻璃模糊度 (Blur Radius):")
        lbl_blur.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        self.lbl_blur_val = QLabel("0 px")
        self.lbl_blur_val.setStyleSheet("color: #2563EB; font-weight: bold;")
        blur_header.addWidget(lbl_blur)
        blur_header.addStretch()
        blur_header.addWidget(self.lbl_blur_val)
        layout.addLayout(blur_header)

        self.slider_blur = QSlider(Qt.Horizontal)
        self.slider_blur.setRange(0, 30)
        self.slider_blur.setValue(0)
        self.slider_blur.valueChanged.connect(self._on_blur_slider)
        layout.addWidget(self.slider_blur)

        # 6. 表格滚动条 (Scrollbar)
        self.chk_show_scrollbar = QCheckBox("显示表格与列表垂直滑条 (Show Scrollbar)")
        self.chk_show_scrollbar.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        self.chk_show_scrollbar.toggled.connect(self._on_scrollbar_toggled)
        layout.addWidget(self.chk_show_scrollbar)

        lbl_scroll_tip = QLabel("💡 默认隐藏以呈现极简纯净界面；隐藏后仍可通过鼠标滚轮或触控板手势自然平滑滚动。")
        lbl_scroll_tip.setStyleSheet("color: #64748B; font-size: 11px;")
        lbl_scroll_tip.setWordWrap(True)
        layout.addWidget(lbl_scroll_tip)

        layout.addStretch()
        return widget

    # --------------------------------------------------------
    # 栏目 2: 屏幕常亮防休眠 (Awake)
    # --------------------------------------------------------
    def _create_tab_awake(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. 启用屏幕常亮
        self.chk_awake = QCheckBox("启用屏幕常亮防息屏 (阻止电脑黑屏休眠 / 自动锁定)")
        self.chk_awake.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        self.chk_awake.toggled.connect(self._on_awake_toggled)
        layout.addWidget(self.chk_awake)

        lbl_awake_desc = QLabel("💡 基于 Windows 原生系统级电源状态调度，0% CPU 占用、无鼠标晃动干扰。")
        lbl_awake_desc.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(lbl_awake_desc)

        # 2. 模式与时长子部件
        self.awake_sub_widget = QWidget()
        layout_sub = QVBoxLayout(self.awake_sub_widget)
        layout_sub.setContentsMargins(20, 4, 0, 4)
        layout_sub.setSpacing(10)

        self.radio_awake_indefinite = QRadioButton("持续常亮 (直到手动关闭或退出软件)")
        self.radio_awake_timed = QRadioButton("定时常亮 (达到设定时间后自动恢复正常休眠)")
        self.btn_grp_awake = QButtonGroup(self)
        self.btn_grp_awake.addButton(self.radio_awake_indefinite)
        self.btn_grp_awake.addButton(self.radio_awake_timed)
        layout_sub.addWidget(self.radio_awake_indefinite)
        layout_sub.addWidget(self.radio_awake_timed)

        # 定时时长行
        timed_box = QHBoxLayout()
        timed_box.setSpacing(8)
        lbl_hours = QLabel("常亮时长:")
        lbl_hours.setFont(QFont("JetBrains Mono", 10))
        timed_box.addWidget(lbl_hours)

        self.spin_awake_hours = QSpinBox()
        self.spin_awake_hours.setRange(1, 48)
        self.spin_awake_hours.setValue(2)
        self.spin_awake_hours.setSuffix(" 小时")
        self.spin_awake_hours.setFixedWidth(100)
        self.spin_awake_hours.setFixedHeight(32)
        timed_box.addWidget(self.spin_awake_hours)

        for h in [1, 2, 4, 8]:
            btn_h = QPushButton(f"{h}h")
            btn_h.setObjectName("btn_hour_preset")
            btn_h.setFixedWidth(52)
            btn_h.setFixedHeight(32)
            btn_h.setCursor(Qt.PointingHandCursor)
            btn_h.clicked.connect(lambda _, val=h: self.spin_awake_hours.setValue(val))
            timed_box.addWidget(btn_h)
        timed_box.addStretch()
        layout_sub.addLayout(timed_box)

        layout.addWidget(self.awake_sub_widget)

        # 3. 实时状态卡片
        status_card = QFrame()
        status_card.setObjectName("card_status")
        status_card_layout = QHBoxLayout(status_card)
        status_card_layout.setContentsMargins(12, 10, 12, 10)

        lbl_status_tag = QLabel("当前运行状态:")
        lbl_status_tag.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        self.lbl_awake_status = QLabel("未开启")
        self.lbl_awake_status.setStyleSheet("color: #2563EB; font-weight: bold;")
        status_card_layout.addWidget(lbl_status_tag)
        status_card_layout.addWidget(self.lbl_awake_status)
        status_card_layout.addStretch()
        layout.addWidget(status_card)

        # 接入 AwakeManager 状态同步
        mgr = AwakeManager.get_instance()
        self.lbl_awake_status.setText(mgr.get_status_text())
        mgr.state_changed.connect(lambda _, txt: self.lbl_awake_status.setText(txt))

        layout.addStretch()
        return widget

    # --------------------------------------------------------
    # 栏目 3: 常规与行为 (含开机自启与静默托盘)
    # --------------------------------------------------------
    def _create_tab_behavior(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        # 1. 系统启动行为：开机自启 与 启动后隐藏到托盘 为两项独立开关
        lbl_autostart = QLabel("系统启动行为 (Startup):")
        lbl_autostart.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(lbl_autostart)

        self.chk_autostart = QCheckBox("开机自动启动 (随 Windows 登录自动运行)")
        self.chk_autostart.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(self.chk_autostart)

        self.chk_start_minimized = QCheckBox("启动后隐藏到系统托盘 (不弹出主窗口)")
        self.chk_start_minimized.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(self.chk_start_minimized)

        lbl_autostart_tip = QLabel("💡 两项互不影响：可以开机自启并正常显示窗口，也可以只在手动启动时静默进托盘。")
        lbl_autostart_tip.setStyleSheet("color: #64748B; font-size: 11px;")
        lbl_autostart_tip.setWordWrap(True)
        layout.addWidget(lbl_autostart_tip)

        # 分割微线
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line1)

        # 2. 关闭主窗口行为
        lbl_close = QLabel("关闭主窗口时的行为 (Close Window Behavior):")
        lbl_close.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(lbl_close)

        self.radio_close_tray = QRadioButton("1. 最小化并隐藏到系统托盘 (推荐，防息屏与托盘继续工作)")
        self.radio_close_exit = QRadioButton("2. 直接退出程序 (释放全部系统电源与后台资源)")
        self.btn_grp_close = QButtonGroup(self)
        self.btn_grp_close.addButton(self.radio_close_tray)
        self.btn_grp_close.addButton(self.radio_close_exit)
        layout.addWidget(self.radio_close_tray)
        layout.addWidget(self.radio_close_exit)

        # 分割微线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)

        # 3. 默认工作与报表导出路径 (可直接键盘手动输入任意路径)
        lbl_path = QLabel("默认工作与报表导出路径 (Default Path):")
        lbl_path.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(lbl_path)

        path_input_layout = QHBoxLayout()
        self.edit_custom_path = QLineEdit()
        self.edit_custom_path.setPlaceholderText("例如: D:\\Software\\NoOvertime 或 E:\\NoOvertime")
        btn_browse_path = QPushButton("浏览文件夹...")
        btn_browse_path.setCursor(Qt.PointingHandCursor)
        btn_browse_path.clicked.connect(self._browse_custom_path)

        path_input_layout.addWidget(self.edit_custom_path, 1)
        path_input_layout.addWidget(btn_browse_path)
        layout.addLayout(path_input_layout)

        lbl_path_tip = QLabel("💡 提示：输入框支持键盘手动输入或粘贴任意盘符目录，报表导出将优先保存至此。")
        lbl_path_tip.setStyleSheet("color: #64748B; font-size: 11px;")
        lbl_path_tip.setWordWrap(True)
        layout.addWidget(lbl_path_tip)

        # 分割微线 (Edge 区域)
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line3)

        # 4. Microsoft Edge 浏览器执行路径 (隐藏，需连续点击标题 10 次才显示)
        lbl_edge = QLabel("Microsoft Edge 浏览器路径 (Edge Executable):")
        lbl_edge.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(lbl_edge)

        edge_input_widget = QWidget()
        edge_input_layout = QHBoxLayout(edge_input_widget)
        edge_input_layout.setContentsMargins(0, 0, 0, 0)
        self.edit_edge_path = QLineEdit()
        self.edit_edge_path.setPlaceholderText("程序首次启动已自动检索；支持手动指定 msedge.exe")
        btn_browse_edge = QPushButton("浏览...")
        btn_browse_edge.setCursor(Qt.PointingHandCursor)
        btn_browse_edge.clicked.connect(self._browse_edge_path)
        btn_detect_edge = QPushButton("重新探测")
        btn_detect_edge.setCursor(Qt.PointingHandCursor)
        btn_detect_edge.clicked.connect(self._auto_detect_edge)

        edge_input_layout.addWidget(self.edit_edge_path, 1)
        edge_input_layout.addWidget(btn_browse_edge)
        edge_input_layout.addWidget(btn_detect_edge)
        layout.addWidget(edge_input_widget)

        lbl_edge_tip = QLabel("💡 提示：首次启动已自动写入配置；若使用绿色便携版或自定义路径，可在此直接浏览选择。")
        lbl_edge_tip.setStyleSheet("color: #64748B; font-size: 11px;")
        lbl_edge_tip.setWordWrap(True)
        layout.addWidget(lbl_edge_tip)

        # 默认隐藏 Edge 路径相关控件
        self._edge_widgets = [line3, lbl_edge, edge_input_widget, lbl_edge_tip]
        for w in self._edge_widgets:
            w.setVisible(False)

        # 5. 调试模式 (演示数据等仅供排查问题使用的入口)
        lbl_debug = QLabel("调试与诊断 (Debug):")
        lbl_debug.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(lbl_debug)

        self.chk_debug = QCheckBox("启用调试模式 (在主界面显示【加载演示数据】按钮)")
        self.chk_debug.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
        layout.addWidget(self.chk_debug)

        lbl_debug_tip = QLabel("💡 演示数据不访问 HR 系统，仅用于本地核对表格与导出格式；日常使用请保持关闭。")
        lbl_debug_tip.setStyleSheet("color: #64748B; font-size: 11px;")
        lbl_debug_tip.setWordWrap(True)
        layout.addWidget(lbl_debug_tip)

        layout.addStretch()
        return widget

    # --------------------------------------------------------
    # 样式与主题更新
    # --------------------------------------------------------
    def apply_dialog_style(self, is_dark: bool):
        bg = "#0F172A" if is_dark else "#F8FAFC"
        card_bg = "#1E293B" if is_dark else "#FFFFFF"
        border = "#334155" if is_dark else "#E2E8F0"
        text = "#F8FAFC" if is_dark else "#0F172A"
        subtext = "#94A3B8" if is_dark else "#475569"
        input_bg = "#0F172A" if is_dark else "#FFFFFF"
        btn_sec_bg = "#1E293B" if is_dark else "#FFFFFF"
        btn_sec_hover = "#334155" if is_dark else "#F1F5F9"
        active_blue = "#3B82F6" if is_dark else "#2563EB"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
                font-family: 'JetBrains Mono', 'Segoe UI', '微软雅黑', sans-serif;
            }}
            QTabWidget::pane {{
                border: 1px solid {border};
                border-radius: 8px;
                background-color: {card_bg};
            }}
            QTabWidget::tab-bar {{
                left: 6px;
            }}
            QTabBar {{
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {subtext};
                padding: 5px 14px;
                min-height: 16px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: 6px;
            }}
            QTabBar::tab:selected {{
                color: {text};
                border-bottom: 2px solid {text};
            }}
            QTabBar::tab:hover:!selected {{
                color: {text};
            }}
            QScrollArea#tab_scroll, QScrollArea#tab_scroll > QWidget > QWidget {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {border};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {subtext};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QLabel {{
                color: {text};
                font-size: 12px;
            }}
            QFrame#card_status {{
                background-color: {input_bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QLineEdit, QSpinBox {{
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                background-color: {input_bg};
                color: {text};
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 1.5px solid {active_blue};
            }}
            QRadioButton, QCheckBox {{
                font-size: 12px;
                color: {text};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {border};
                border-radius: 3px;
                background-color: {input_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {active_blue};
                border: 1px solid {active_blue};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {border};
                height: 6px;
                background: {input_bg};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {active_blue};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {active_blue};
                border: 2px solid #FFFFFF;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }}
            QPushButton {{
                font-size: 12px;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
                background-color: {btn_sec_bg};
                color: {subtext};
                border: 1px solid {border};
            }}
            QPushButton:hover {{
                background-color: {btn_sec_hover};
                color: {text};
            }}
            QPushButton#btn_primary {{
                background-color: {active_blue};
                color: #FFFFFF;
                border: none;
            }}
            QPushButton#btn_primary:hover {{
                background-color: #1D4ED8;
            }}
            QPushButton#btn_hour_preset {{
                padding: 0px;
                font-size: 13px;
                font-weight: bold;
                text-align: center;
                border-radius: 6px;
                background-color: {btn_sec_bg};
                color: {text};
                border: 1px solid {border};
            }}
            QPushButton#btn_hour_preset:hover {{
                background-color: {btn_sec_hover};
                border-color: {active_blue};
                color: {active_blue};
            }}
        """)

    def _on_awake_toggled(self, checked: bool):
        self.awake_sub_widget.setEnabled(checked)

    def load_values(self):
        # 1. 外观栏目
        if self.config.get("theme", "light") == "dark":
            self.radio_dark.setChecked(True)
        else:
            self.radio_light.setChecked(True)

        self.edit_bg_path.setText(self.config.get("bg_image_path", ""))

        op = int(self.config.get("window_opacity", 100))
        self.slider_opacity.setValue(op)
        self.lbl_opacity_val.setText(f"{op}%")

        mask = int(self.config.get("mask_density", 20))
        self.slider_mask.setValue(mask)
        self.lbl_mask_val.setText(f"{mask}%")

        blur = int(self.config.get("blur_radius", 0))
        self.slider_blur.setValue(blur)
        self.lbl_blur_val.setText(f"{blur} px")

        self.chk_show_scrollbar.setChecked(bool(self.config.get("show_scrollbar", False)))

        # 2. 屏幕常亮栏目
        awake_en = bool(self.config.get("awake_enabled", False))
        self.chk_awake.setChecked(awake_en)
        self.awake_sub_widget.setEnabled(awake_en)

        if self.config.get("awake_mode", "indefinite") == "timed":
            self.radio_awake_timed.setChecked(True)
        else:
            self.radio_awake_indefinite.setChecked(True)

        self.spin_awake_hours.setValue(int(self.config.get("awake_hours", 2)))

        # 3. 常规与行为栏目
        # 开机自启：优先检查系统注册表或配置
        autostart_cfg = bool(self.config.get("autostart", False))
        autostart_reg = is_autostart_enabled()
        self.chk_autostart.setChecked(autostart_cfg or autostart_reg)
        self.chk_start_minimized.setChecked(bool(self.config.get("start_minimized", False)))

        if self.config.get("close_action", "tray") == "exit":
            self.radio_close_exit.setChecked(True)
        else:
            self.radio_close_tray.setChecked(True)

        self.edit_custom_path.setText(self.config.get("custom_export_path", ""))
        self.edit_edge_path.setText(self.config.get("edge_path", ""))
        self.chk_debug.setChecked(bool(self.config.get("debug_mode", False)))

    def _on_theme_changed(self):
        is_dark = self.radio_dark.isChecked()
        self.apply_dialog_style(is_dark)

    def _browse_bg_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self.edit_bg_path.setText(path)

    def _clear_bg_image(self):
        self.edit_bg_path.clear()

    def _browse_custom_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择默认工作/导出路径", self.edit_custom_path.text().strip())
        if d:
            self.edit_custom_path.setText(d)

    def _browse_edge_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Microsoft Edge 执行程序", self.edit_edge_path.text().strip(), "可执行文件 (msedge.exe *.exe);;所有文件 (*.*)"
        )
        if path:
            self.edit_edge_path.setText(path)

    def _auto_detect_edge(self):
        try:
            from core.edge_cdp import find_edge_binary
            detected = find_edge_binary()
            if detected and os.path.exists(detected):
                self.edit_edge_path.setText(detected)
                StyledMessageBox(
                    self,
                    title="探测成功",
                    headline="成功检测到 Edge 浏览器安装路径",
                    message=f"已自动定位: \n{detected}",
                    icon_type="success"
                ).exec_()
        except Exception as e:
            StyledMessageBox(
                self,
                title="探测失败",
                headline="未在系统中自动检测到 Edge",
                message=str(e),
                icon_type="warning"
            ).exec_()

    def _on_opacity_slider(self, val: int):
        self.lbl_opacity_val.setText(f"{val}%")

    def _on_mask_slider(self, val: int):
        self.lbl_mask_val.setText(f"{val}%")

    def _on_blur_slider(self, val: int):
        self.lbl_blur_val.setText(f"{val} px")

    def get_current_settings(self) -> dict:
        return {
            "theme": "dark" if self.radio_dark.isChecked() else "light",
            "bg_image_path": self.edit_bg_path.text().strip(),
            "window_opacity": self.slider_opacity.value(),
            "mask_density": self.slider_mask.value(),
            "blur_radius": self.slider_blur.value(),
            "awake_enabled": self.chk_awake.isChecked(),
            "awake_mode": "timed" if self.radio_awake_timed.isChecked() else "indefinite",
            "awake_hours": self.spin_awake_hours.value(),
            "autostart": self.chk_autostart.isChecked(),
            "start_minimized": self.chk_start_minimized.isChecked(),
            "close_action": "exit" if self.radio_close_exit.isChecked() else "tray",
            "custom_export_path": self.edit_custom_path.text().strip(),
            "edge_path": self.edit_edge_path.text().strip(),
            "debug_mode": self.chk_debug.isChecked(),
            "show_scrollbar": self.chk_show_scrollbar.isChecked()
        }

    def _on_scrollbar_toggled(self, checked: bool):
        cur = self.get_current_settings()
        self.settings_changed.emit(cur)

    def _on_apply(self):
        cur = self.get_current_settings()
        self.config.update(cur)
        # 即时写入注册表开机自启 (是否静默进托盘由独立开关决定)
        set_autostart(cur["autostart"], cur["start_minimized"])
        self.settings_changed.emit(self.config)

    def _on_ok(self):
        self._on_apply()
        self.accept()

    def _on_cancel(self):
        self.settings_changed.emit(self.original_config)
        self.reject()

    # --------------------------------------------------------
    # 隐藏开发者入口：连续点击标题 10 次显示 Edge 路径配置
    # --------------------------------------------------------
    def _on_title_clicked(self, event):
        self._edge_click_count += 1
        remaining = 10 - self._edge_click_count
        if remaining > 0 and remaining <= 3:
            # 最后 3 次给出倒计提示
            self.lbl_title.setToolTip(f"再点击 {remaining} 次即可进入开发者设置")
        if self._edge_click_count >= 10:
            for w in self._edge_widgets:
                w.setVisible(True)
            self._edge_click_count = 0
            self.lbl_title.setToolTip("")

    def closeEvent(self, event):
        """关闭设置对话框时重置隐藏状态"""
        self._edge_click_count = 0
        for w in self._edge_widgets:
            w.setVisible(False)
        self.lbl_title.setToolTip("")
        super().closeEvent(event)
