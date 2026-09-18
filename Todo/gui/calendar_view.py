import calendar
from datetime import date
from typing import List, Dict, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor


class DayCellWidget(QFrame):
    """单个日期卡片方格"""
    def __init__(self, day_data: Optional[Dict[str, Any]] = None, day_num: int = 0, is_cur_month: bool = True, is_dark: bool = False):
        super().__init__()
        self.day_data = day_data
        self.day_num = day_num
        self.is_cur_month = is_cur_month
        self.is_dark = is_dark
        self.init_ui()

    def init_ui(self):
        self.setMinimumHeight(105)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)

        if not self.is_cur_month or not self.day_data:
            # 非当月占位格
            bg = "#0F172A" if self.is_dark else "#F8FAFC"
            border = "#334155" if self.is_dark else "#E2E8F0"
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg};
                    border: 1px dashed {border};
                    border-radius: 6px;
                }}
            """)
            if self.day_num > 0:
                lbl = QLabel(str(self.day_num))
                lbl.setFont(QFont("JetBrains Mono", 10))
                lbl.setStyleSheet("color: #475569;" if self.is_dark else "color: #CBD5E1;")
                layout.addWidget(lbl)
            layout.addStretch()
            return

        ot = float(self.day_data.get("overtime_hours", 0.0))
        detail_type = self.day_data.get("detail_type", "")
        is_holiday = detail_type == "法定节假日"
        is_weekend = self.day_data.get("is_weekend", False)
        shift = self.day_data.get("shift_name", "")
        cin = self.day_data.get("check_in", "-")
        cout = self.day_data.get("check_out", "-")

        # 单元格边框与底色
        if self.is_dark:
            if is_holiday:
                bg_style = "background-color: #451A1A; border: 1.5px solid #7F1D1D;"
            elif ot > 0:
                if detail_type == "周末加班":
                    bg_style = "background-color: #78350F; border: 1.5px solid #D97706;"
                else:
                    bg_style = "background-color: #064E3B; border: 1.5px solid #059669;"
            elif detail_type == "公休":
                bg_style = "background-color: #1E293B; border: 1px solid #334155;"
            else:
                bg_style = "background-color: #1E293B; border: 1px solid #334155;"
        else:
            if is_holiday:
                bg_style = "background-color: #FEF2F2; border: 1.5px solid #FECACA;"
            elif ot > 0:
                if detail_type == "周末加班":
                    bg_style = "background-color: #FFFBEB; border: 1.5px solid #FDE68A;"
                else:
                    bg_style = "background-color: #F0FDF4; border: 1.5px solid #BBF7D0;"
            elif detail_type == "公休":
                bg_style = "background-color: #F8FAFC; border: 1px solid #E2E8F0;"
            else:
                bg_style = "background-color: #FFFFFF; border: 1px solid #E2E8F0;"

        self.setStyleSheet(f"""
            QFrame {{
                {bg_style}
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 1.5px solid #2563EB;
            }}
        """)

        # 1. 顶部：日期号 + 节假日/周末标签
        top_box = QHBoxLayout()
        top_box.setSpacing(4)
        
        lbl_day = QLabel(f"{self.day_num:02d}")
        lbl_day.setFont(QFont("JetBrains Mono", 12, QFont.Bold))
        if self.is_dark:
            day_color = "color: #F8FAFC;" if not is_weekend else "color: #94A3B8;"
        else:
            day_color = "color: #0F172A;" if not is_weekend else "color: #64748B;"
        lbl_day.setStyleSheet(day_color)
        top_box.addWidget(lbl_day)

        if is_holiday:
            tag_hol = QLabel("节")
            tag_hol.setStyleSheet("background-color: #EF4444; color: #FFFFFF; border-radius: 3px; font-size: 10px; font-weight: bold; padding: 1px 4px;")
            top_box.addWidget(tag_hol)
        elif is_weekend:
            tag_wk = QLabel("休" if detail_type == "公休" else "末")
            tag_wk_style = "background-color: #334155; color: #CBD5E1;" if self.is_dark else "background-color: #E2E8F0; color: #475569;"
            tag_wk.setStyleSheet(f"{tag_wk_style} border-radius: 3px; font-size: 10px; padding: 1px 3px;")
            top_box.addWidget(tag_wk)

        top_box.addStretch()

        # 班次名称精简
        short_shift = shift.split("(")[0].strip() if shift else ""
        if len(short_shift) > 8:
            short_shift = short_shift[:8]
        lbl_shift = QLabel(short_shift)
        lbl_shift.setFont(QFont("JetBrains Mono", 9))
        lbl_shift.setStyleSheet("color: #64748B;" if not self.is_dark else "color: #94A3B8;")
        top_box.addWidget(lbl_shift)
        
        layout.addLayout(top_box)

        # 2. 中间：上下班打卡时间
        time_text = f"{cin} ~ {cout}" if (cin != "-" or cout != "-") else "未打卡 / 无记录"
        lbl_time = QLabel(time_text)
        lbl_time.setFont(QFont("JetBrains Mono", 9))
        if cin != "-" or cout != "-":
            lbl_time.setStyleSheet("color: #F8FAFC; font-weight: bold;" if self.is_dark else "color: #0F172A; font-weight: bold;")
        else:
            lbl_time.setStyleSheet("color: #64748B;" if self.is_dark else "color: #94A3B8;")
        layout.addWidget(lbl_time)

        # 3. 底部：加班工时标签
        ot_box = QHBoxLayout()
        if ot > 0:
            if is_holiday:
                lbl_ot = QLabel(f"⏱ {ot:.1f}h (不计)")
                lbl_ot.setStyleSheet("background-color: #FEE2E2; color: #B91C1C; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px;")
            elif detail_type == "周末加班":
                lbl_ot = QLabel(f"⏱ +{ot:.1f}h 周末")
                lbl_ot.setStyleSheet("background-color: #FEF3C7; color: #B45309; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px;")
            else:
                lbl_ot = QLabel(f"⏱ +{ot:.1f}h 加班")
                lbl_ot.setStyleSheet("background-color: #DCFCE7; color: #15803D; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px;")
            ot_box.addWidget(lbl_ot)
        else:
            lbl_status = QLabel("正常工时" if detail_type != "公休" else "公休放假")
            lbl_status.setStyleSheet("color: #64748B; font-size: 10px;" if self.is_dark else "color: #94A3B8; font-size: 10px;")
            ot_box.addWidget(lbl_status)
            
        ot_box.addStretch()
        layout.addLayout(ot_box)


class AttendanceCalendarWidget(QWidget):
    """月度考勤与加班日历看板视图"""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.records: List[Dict[str, Any]] = []
        self.year = 2026
        self.month = 9
        self.is_dark = False
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        # 星期表头 (周一 至 周日)
        self.header_widget = QWidget()
        h_layout = QHBoxLayout(self.header_widget)
        h_layout.setContentsMargins(2, 0, 2, 0)
        h_layout.setSpacing(6)
        
        weekdays = ["周一 MON", "周二 TUE", "周三 WED", "周四 THU", "周五 FRI", "周六 SAT", "周日 SUN"]
        for idx, w in enumerate(weekdays):
            lbl = QLabel(w)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFont(QFont("JetBrains Mono", 10, QFont.Bold))
            if idx in [5, 6]:
                lbl.setStyleSheet("background-color: #334155; color: #E2E8F0; padding: 6px; border-radius: 4px;")
            else:
                lbl.setStyleSheet("background-color: #1E293B; color: #FFFFFF; padding: 6px; border-radius: 4px;")
            h_layout.addWidget(lbl, 1)
            
        main_layout.addWidget(self.header_widget)

        # 滚动区域包装日历网格
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background-color: #FFFFFF;
            }
        """)
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(6, 6, 6, 6)
        self.grid_layout.setSpacing(6)
        
        self.scroll.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll, 1)

    def set_dark_mode(self, is_dark: bool):
        self.is_dark = is_dark
        border = "#334155" if is_dark else "#E2E8F0"
        bg = "#1E293B" if is_dark else "#FFFFFF"
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {border};
                border-radius: 8px;
                background-color: {bg};
            }}
        """)
        if self.records:
            self.update_calendar(self.year, self.month, self.records)

    def update_calendar(self, year: int, month: int, records: List[Dict[str, Any]]):
        self.year = year
        self.month = month
        self.records = records

        # 清空现有网格
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # 索引化当前记录 (以日为 key)
        record_map = {}
        for r in records:
            d_str = r.get("date", "")
            try:
                dt = date.fromisoformat(d_str)
                record_map[dt.day] = r
            except Exception:
                pass

        first_weekday, num_days = calendar.monthrange(year, month)

        # 填充上月末尾占位格
        row = 0
        col = 0
        for i in range(first_weekday):
            dummy = DayCellWidget(day_data=None, day_num=0, is_cur_month=False, is_dark=self.is_dark)
            self.grid_layout.addWidget(dummy, row, col)
            col += 1

        # 填充当月每日
        for d in range(1, num_days + 1):
            day_data = record_map.get(d, {
                "date": f"{year:04d}-{month:02d}-{d:02d}",
                "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][(first_weekday + d - 1) % 7],
                "check_in": "-",
                "check_out": "-",
                "overtime_hours": 0.0,
                "shift_name": "未排班",
                "detail_type": "正常工时",
                "is_weekend": (first_weekday + d - 1) % 7 in [5, 6]
            })
            cell = DayCellWidget(day_data=day_data, day_num=d, is_cur_month=True, is_dark=self.is_dark)
            self.grid_layout.addWidget(cell, row, col)
            
            col += 1
            if col == 7:
                col = 0
                row += 1

        # 填充下月月初占位格，补齐最后一行
        if col > 0:
            for i in range(col, 7):
                dummy = DayCellWidget(day_data=None, day_num=0, is_cur_month=False, is_dark=self.is_dark)
                self.grid_layout.addWidget(dummy, row, i)
