"""
日历视图班次展示格式化单元测试
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
for p in [SRC_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from gui.calendar_view import format_shift_name


class TestCalendarShiftFormatting:
    def test_fullwidth_chinese_bracket(self):
        # 实际 PeoPlus 常见的全角括号格式
        assert format_shift_name("SD3-职员白班（08:30-17:30）") == "白班"
        assert format_shift_name("SD3-职员公休白班（08:30-17:30）") == "公休白班"

    def test_halfwidth_bracket(self):
        # 半角括号格式
        assert format_shift_name("SD3-职员白班 (08:30-17:30)") == "白班"
        assert format_shift_name("SD3-职员公休白班 (08:30-17:30)") == "公休白班"

    def test_clean_rest_shift(self):
        # 公休班次
        assert format_shift_name("SD3-职员公休") == "公休"

    def test_pure_shift(self):
        # 无前缀班次
        assert format_shift_name("白班 (08:30-17:30)") == "白班"
        assert format_shift_name("白班（08:30-17:30）") == "白班"
        assert format_shift_name("白班") == "白班"
        assert format_shift_name("公休") == "公休"
        assert format_shift_name("未排班") == "未排班"

    def test_empty_or_none(self):
        assert format_shift_name("") == ""
        assert format_shift_name(None) == ""
