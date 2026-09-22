"""
加班核算规则单元测试

覆盖: 跨天下班、次日 02:00 最晚截止、起算线与颗粒度、
      标准班次午休扣除、法定节假日/公休/周末加班单优先级
运行: python -m pytest tests -q
"""
import os
import sys
from datetime import date

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
for p in [SRC_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.calculator import (  # noqa: E402
    calculate_daily_overtime,
    calculate_overtime_allowance,
    standard_work_hours,
    parse_time_str
)

# 2026-09-14 周一, 09-19 周六
MONDAY = date(2026, 9, 14)
SATURDAY = date(2026, 9, 19)
SHIFT_DAY = "SD3-职员白班 (08:30-17:30)"
SHIFT_REST = "SD3-职员公休"


def ot(record_date, cin, cout, **kw) -> float:
    return calculate_daily_overtime(
        record_date=record_date, shift_name=kw.pop("shift", SHIFT_DAY),
        check_in_str=cin, check_out_str=cout, **kw
    )["overtime_hours"]


class TestWeekdayOvertime:
    def test_before_ot_start_no_overtime(self):
        assert ot(MONDAY, "08:15", "17:40") == 0.0

    def test_below_min_threshold_not_counted(self):
        # 18:29 距 18:00 仅 29 分钟，未满 30 分钟起算线
        assert ot(MONDAY, "08:15", "18:29") == 0.0

    def test_granularity_floor(self):
        assert ot(MONDAY, "08:15", "18:30") == 0.5
        assert ot(MONDAY, "08:15", "18:59") == 0.5
        assert ot(MONDAY, "08:15", "21:31") == 3.5


class TestCrossDayOvertime:
    """跨天下班：加班到次日凌晨"""

    def test_time_only_string_rolls_to_next_day(self):
        # 只带时间的 '00:30' 会被解析成当天 00:30，必须自动对齐到次日
        assert ot(MONDAY, "08:15", "00:30") == 6.5

    def test_explicit_next_day_string(self):
        assert ot(MONDAY, "09-14 08:15", "09-15 01:00") == 7.0

    def test_capped_at_two_am(self):
        # 02:00 为最晚截止，02:00~03:40 部分不计
        assert ot(MONDAY, "08:15", "02:00") == 8.0
        assert ot(MONDAY, "08:15", "03:40") == 8.0

    def test_cap_note_records_dropped_minutes(self):
        r = calculate_daily_overtime(MONDAY, SHIFT_DAY, "08:15", "03:40")
        assert "次日凌晨下班" in r["notes"]
        assert "100分钟不计" in r["notes"]

    def test_exactly_two_am_boundary_no_drop_note(self):
        r = calculate_daily_overtime(MONDAY, SHIFT_DAY, "08:15", "02:00")
        assert "不计" not in r["notes"]

    def test_custom_latest_end(self):
        assert ot(MONDAY, "08:15", "03:40", ot_latest_end="04:00") == 9.5

    def test_no_check_out(self):
        r = calculate_daily_overtime(MONDAY, SHIFT_DAY, "08:15", "-")
        assert r["overtime_hours"] == 0.0
        assert r["detail_type"] == "正常工时"


class TestStandardWorkHours:
    """标准班次 08:30-12:00 / 13:00-17:30，午休 12:00-13:00 不计工时"""

    def test_full_day_is_eight_hours(self):
        cin = parse_time_str(SATURDAY, "08:30")
        cout = parse_time_str(SATURDAY, "17:30")
        assert standard_work_hours(SATURDAY, cin, cout) == 8.0

    def test_lunch_break_excluded(self):
        # 08:30-15:00 = 3.5h(上午) + 2.0h(下午)，不含午休 1 小时
        cin = parse_time_str(SATURDAY, "08:30")
        cout = parse_time_str(SATURDAY, "15:00")
        assert standard_work_hours(SATURDAY, cin, cout) == 5.5

    def test_outside_shift_not_counted(self):
        cin = parse_time_str(SATURDAY, "12:10")
        cout = parse_time_str(SATURDAY, "12:50")
        assert standard_work_hours(SATURDAY, cin, cout) == 0.0


class TestWeekendAndHoliday:
    def test_approved_hours_take_priority(self):
        assert ot(SATURDAY, "08:20", "18:10", ot_valid_hours=8.0) == 8.0

    def test_approved_zero_hours_means_no_overtime(self):
        r = calculate_daily_overtime(SATURDAY, SHIFT_REST, "-", "-", ot_valid_hours=0.0)
        assert r["overtime_hours"] == 0.0
        assert r["detail_type"] == "公休"

    def test_public_holiday_shift_excluded(self):
        r = calculate_daily_overtime(SATURDAY, SHIFT_REST, "08:20", "20:00")
        assert r["overtime_hours"] == 0.0

    def test_statutory_holiday_excluded(self):
        # 5.1 法定节假日（带“节”角标），即便审批单有有效时长也不计入该月常规加班
        r = calculate_daily_overtime(
            date(2026, 5, 1), "SD3-职员公休白班 (08:30-17:30)", "08:12", "20:33",
            ot_valid_hours=10.5, is_statutory_holiday=True
        )
        assert r["overtime_hours"] == 0.0
        assert r["detail_type"] == "法定节假日"
        assert "不计入该月加班" in r["notes"]

    def test_makeup_workday_sept20_off_before_six(self):
        # 9.20 周日调休正常上班，时段1有打卡且18:00前下班，不计入加班（0.0h，修补原误算8.0h的Bug）
        r = calculate_daily_overtime(
            date(2026, 9, 20), SHIFT_DAY, "08:08", "17:33",
            has_slot1_punch=True
        )
        assert r["overtime_hours"] == 0.0
        assert r["detail_type"] == "正常工时"
        assert "18:00前下班，无加班" in r["notes"]

    def test_makeup_workday_may09_overtime_after_six(self):
        # 5.9 周六调休正常上班，时段1打卡08:10-20:31，无有效加班时长，按18:00后计2.5h延时加班
        r = calculate_daily_overtime(
            date(2026, 5, 9), SHIFT_DAY, "08:10", "20:31",
            has_slot1_punch=True
        )
        assert r["overtime_hours"] == 2.5
        assert r["detail_type"] == "周内加班"
        assert "18:00后延时加班 151分钟，计 2.5小时" in r["notes"]

    def test_weekend_rest_day_may17_with_approved_hours(self):
        # 5.17 周日公休，时段1无考勤打卡，但加班信息有有效加班时长4.5h
        r = calculate_daily_overtime(
            date(2026, 5, 17), "SD3-职员公休白班 (08:30-17:30)", "12:52", "17:36",
            ot_valid_hours=4.5, has_slot1_punch=False
        )
        assert r["overtime_hours"] == 4.5
        assert r["detail_type"] == "周末加班"
        assert "周末有效加班时长: 4.5小时" in r["notes"]

    def test_weekend_rest_day_unpunched_fallback(self):
        # 周末非正常班次（时段1未打卡）且无审批单时，按兜底规则计算基础工时+延时
        assert ot(SATURDAY, "08:20", "20:00", has_slot1_punch=False, include_weekend_base=True) == 10.0
        assert ot(SATURDAY, "08:20", "20:00", has_slot1_punch=False, include_weekend_base=False) == 0.0
        assert ot(SATURDAY, "08:20", "03:00", has_slot1_punch=False, include_weekend_base=True) == 16.0


class TestTimeParsing:
    def test_leap_day_month_day_string(self):
        assert parse_time_str(date(2028, 2, 29), "02-29 08:18") == parse_time_str(
            date(2028, 2, 29), "2028-02-29 08:18"
        )

    def test_cross_year_month_day_string(self):
        # 考勤日 12-31，下班打卡记为次年 01-01 01:30
        dt = parse_time_str(date(2026, 12, 31), "01-01 01:30")
        assert (dt.year, dt.month, dt.day) == (2027, 1, 1)

    def test_cross_year_overtime(self):
        assert ot(date(2026, 12, 31), "08:15", "01-01 01:30") == 7.5


class TestRobustness:
    def test_zero_granularity_does_not_crash(self):
        assert ot(MONDAY, "08:15", "21:31", granularity_minutes=0) >= 0.0

    def test_invalid_time_config_falls_back(self):
        assert ot(MONDAY, "08:15", "21:31", weekday_ot_start="bad", ot_latest_end="") == 3.5


class TestAllowance:
    def test_tiers(self):
        assert calculate_overtime_allowance(0)[0] == 0
        assert calculate_overtime_allowance(20)[0] == 0
        assert calculate_overtime_allowance(20.5)[0] == 200
        assert calculate_overtime_allowance(36)[0] == 300
        assert calculate_overtime_allowance(85)[0] == 1300
        assert calculate_overtime_allowance(85.5)[0] == 1400
        assert calculate_overtime_allowance(90)[0] == 1400
        assert calculate_overtime_allowance(90.1)[0] == 1500
        assert calculate_overtime_allowance(120)[0] == 1500


if __name__ == "__main__":
    import inspect

    test_classes = [
        TestWeekdayOvertime,
        TestCrossDayOvertime,
        TestStandardWorkHours,
        TestWeekendAndHoliday,
        TestTimeParsing,
        TestRobustness,
        TestAllowance,
    ]
    passed = 0
    failed = 0
    for cls in test_classes:
        instance = cls()
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("test_"):
                try:
                    method(instance)
                    passed += 1
                except Exception as e:
                    print(f"FAILED: {cls.__name__}.{name}: {e}")
                    failed += 1
    print(f"Tests finished: {passed} passed, {failed} failed.")
    if failed:
        sys.exit(1)

