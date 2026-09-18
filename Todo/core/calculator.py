from datetime import datetime, date, time, timedelta
from typing import Dict, Any, Optional, Tuple

# 标准班次时间节点: 上午 08:30-12:00，午休 12:00-13:00 (不计工时)，下午 13:00-17:30
WORK_MORNING_START = time(8, 30)
WORK_MORNING_END = time(12, 0)
WORK_AFTERNOON_START = time(13, 0)
WORK_AFTERNOON_END = time(17, 30)

# 加班最晚计算到次日 02:00，超出部分不再累计
DEFAULT_OT_LATEST_END = "02:00"


def parse_time_str(date_ref: date, t_str: str) -> Optional[datetime]:
    """
    解析打卡时间字符串，格式可能为:
    - '09-01 08:18'
    - '2026-09-01 08:18'
    - '08:18'
    - '-' 或空
    """
    if not t_str or t_str.strip() in ['-', '--', '未打卡', '无']:
        return None
    t_str = t_str.strip()
    
    # 1. 带完整年月日
    for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(t_str, fmt)
        except ValueError:
            continue
            
    # 2. 只带月日 (如 '09-01 08:18')：先补齐考勤日所属年份再解析，
    #    避免 strptime 缺省年份导致的闰日解析失败，并修正跨年错位
    for sep in ("-", "/"):
        try:
            dt = datetime.strptime(f"{date_ref.year}{sep}{t_str}", f"%Y{sep}%m{sep}%d %H:%M")
        except ValueError:
            continue
        delta_days = (dt.date() - date_ref).days
        if delta_days < -300:      # 如考勤日 12-31、打卡 01-01，属次年
            dt = dt.replace(year=date_ref.year + 1)
        elif delta_days > 300:     # 如考勤日 01-01、打卡 12-31，属上一年
            dt = dt.replace(year=date_ref.year - 1)
        return dt
        
    # 3. 只带时间 (如 '08:18')
    try:
        return datetime.combine(date_ref, datetime.strptime(t_str, "%H:%M").time())
    except ValueError:
        return None


def _parse_hhmm(t_str: str, default: time) -> time:
    """解析 'HH:MM' 配置项，非法值回落到默认时刻"""
    try:
        h, m = [int(x) for x in str(t_str).strip().split(":")[:2]]
        return time(h, m)
    except Exception:
        return default


def normalize_check_out(
    record_date: date,
    check_in_dt: Optional[datetime],
    check_out_dt: Optional[datetime]
) -> Optional[datetime]:
    """
    跨天下班对齐。
    加班到次日凌晨时，打卡串往往只带时间 (如 '01:30') 或仍带当日日期，
    直接解析会落在当天，导致时长算成负数、或被误判为“18:00 前下班”。
    """
    if not check_out_dt:
        return None
    if check_in_dt and check_out_dt <= check_in_dt:
        return check_out_dt + timedelta(days=1)
    if check_out_dt.date() == record_date and check_out_dt.time() < WORK_MORNING_START:
        return check_out_dt + timedelta(days=1)
    return check_out_dt


def _overlap_hours(start_dt: datetime, end_dt: datetime, win_start: datetime, win_end: datetime) -> float:
    """区间 [start_dt, end_dt] 与班次时间窗 [win_start, win_end] 的重叠小时数"""
    s = max(start_dt, win_start)
    e = min(end_dt, win_end)
    return max(0.0, (e - s).total_seconds() / 3600.0)


def standard_work_hours(
    record_date: date,
    check_in_dt: Optional[datetime],
    check_out_dt: Optional[datetime],
    afternoon_end: time = WORK_AFTERNOON_END
) -> float:
    """
    按标准班次 (08:30-12:00 / 13:00-17:30) 统计有效出勤工时，
    午休 12:00-13:00 天然被排除，因此部分出勤不会虚高 1 小时
    """
    if not check_in_dt or not check_out_dt or check_out_dt <= check_in_dt:
        return 0.0
    morning = _overlap_hours(
        check_in_dt, check_out_dt,
        datetime.combine(record_date, WORK_MORNING_START),
        datetime.combine(record_date, WORK_MORNING_END)
    )
    afternoon = _overlap_hours(
        check_in_dt, check_out_dt,
        datetime.combine(record_date, WORK_AFTERNOON_START),
        datetime.combine(record_date, afternoon_end)
    )
    return round(morning + afternoon, 2)


def resolve_ot_window(
    record_date: date,
    ot_start_str: str = "18:00",
    ot_latest_end_str: str = DEFAULT_OT_LATEST_END
) -> Tuple[datetime, datetime]:
    """
    返回当日加班的 (起算时刻, 最晚截止时刻)。
    截止时刻不晚于起算时刻时按次日凌晨处理 (如 18:00 起算、次日 02:00 截止)
    """
    ot_start = datetime.combine(record_date, _parse_hhmm(ot_start_str, time(18, 0)))
    cutoff = datetime.combine(record_date, _parse_hhmm(ot_latest_end_str, time(2, 0)))
    if cutoff <= ot_start:
        cutoff += timedelta(days=1)
    return ot_start, cutoff


def _calc_ot_hours(
    ot_start_dt: datetime,
    check_out_dt: datetime,
    cutoff_dt: datetime,
    min_ot_minutes: int,
    granularity_minutes: int
) -> Tuple[float, int, int]:
    """
    按“起算线 + 颗粒度向下取整 + 最晚截止封顶”计算加班
    返回 (计入加班小时, 截止前的加班分钟, 超出最晚截止被舍弃的分钟)
    """
    dropped = max(0, int((check_out_dt - cutoff_dt).total_seconds() // 60))
    effective_out = min(check_out_dt, cutoff_dt)
    if effective_out <= ot_start_dt:
        return 0.0, 0, dropped

    minutes = int((effective_out - ot_start_dt).total_seconds() // 60)
    if minutes < max(0, int(min_ot_minutes)):
        return 0.0, minutes, dropped

    step = max(1, int(granularity_minutes or 0))
    hours = round((minutes // step) * (step / 60.0), 2)
    return hours, minutes, dropped


def calculate_daily_overtime(
    record_date: date,
    shift_name: str,
    check_in_str: str,
    check_out_str: str,
    weekday_standard_end: str = "17:30",
    weekday_ot_start: str = "18:00",
    min_ot_minutes: int = 30,
    granularity_minutes: int = 30,
    ot_valid_hours: Optional[float] = None,
    is_statutory_holiday: bool = False,
    ot_latest_end: str = DEFAULT_OT_LATEST_END,
    include_weekend_base: bool = True
) -> Dict[str, Any]:
    """
    计算单日加班时长

    计算口径:
    - 标准班次 08:30-12:00、13:00-17:30，午休 12:00-13:00 不计工时
    - 17:30-18:00 为晚饭缓冲不计加班，18:00 起开始计算加班
    - 加班最晚计算到次日 02:00 (ot_latest_end)，超出部分不再累计
    - 满 min_ot_minutes (默认 30) 分钟起算，按 granularity_minutes (默认 30) 分钟向下取整
    - 下班打卡落在次日凌晨时自动对齐到次日，不会算成负数或漏算

    规则优先级:
    1. 法定节假日 (日历带“节”角标): 有效加班时长不计入该月加班 (0.0 小时)
    2. 周末且存在审批加班单: 以审批的“有效加班时长”为准
    3. 公休班次且无有效加班单: 不计入加班时长 (0 小时)
    4. 周一至周五: 按上述口径计算 18:00 之后的延时加班
    5. 周末非公休: 标准班次内有效工时 + 18:00 后延时加班 (注明打卡兜底)
    """
    weekday = record_date.weekday()  # 0: Monday ... 4: Friday, 5: Saturday, 6: Sunday
    is_weekend = (weekday in [5, 6])
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday_name = weekday_names[weekday]
    
    is_public_holiday_shift = "公休" in (shift_name or "")
    
    check_in_dt = parse_time_str(record_date, check_in_str)
    check_out_dt = normalize_check_out(record_date, check_in_dt, parse_time_str(record_date, check_out_str))
    
    result = {
        "date": record_date.strftime("%Y-%m-%d"),
        "weekday": weekday_name,
        "is_weekend": is_weekend,
        "shift_name": shift_name or "未排班",
        "check_in": check_in_str or "-",
        "check_out": check_out_str or "-",
        "is_public_holiday": is_statutory_holiday,
        "overtime_hours": 0.0,
        "declared_ot_hours": float(ot_valid_hours or 0.0),
        "detail_type": "正常工时",
        "notes": ""
    }
    
    # 规则 1: 法定节假日（日历带“节”角标）严格排除
    # 用户的明确规则：“节代表节假日，节假日有效加班时长不计入该月加班”
    if is_statutory_holiday:
        result["detail_type"] = "法定节假日"
        if ot_valid_hours and ot_valid_hours > 0:
            result["notes"] = f"法定节假日（节）加班单 {ot_valid_hours}小时，不计入该月加班"
        else:
            result["notes"] = "法定节假日（节），不计入该月加班"
        return result
    
    # 规则 2: 普通周末加班单优先 (只要加班单中有核定的有效加班时长)
    if is_weekend and ot_valid_hours is not None:
        result["overtime_hours"] = float(ot_valid_hours)
        if ot_valid_hours > 0:
            result["detail_type"] = "周末加班"
            result["is_public_holiday"] = False  # 有有效加班的周末不算公休
            result["notes"] = f"周末有效加班时长: {ot_valid_hours}小时"
        else:
            result["detail_type"] = "公休" if is_public_holiday_shift else "正常工时"
            result["is_public_holiday"] = True if is_public_holiday_shift else False
            result["notes"] = "公休班次，无有效加班" if is_public_holiday_shift else "周末无加班"
        return result
        
    # 规则 3: 公休打卡 (无加班单或无有效时长) 不计入加班
    if is_public_holiday_shift:
        result["notes"] = "公休班次，不计入加班时长"
        result["detail_type"] = "公休"
        result["is_public_holiday"] = True
        return result
    
    # 如果下班未打卡或没有打卡记录
    if not check_out_dt:
        result["notes"] = "下班未打卡或无出勤"
        return result
        
    # 加班时间窗: 18:00 起算，最晚计到次日 02:00 (均锚定考勤日，不受跨天打卡影响)
    ot_start_dt, ot_cutoff_dt = resolve_ot_window(record_date, weekday_ot_start, ot_latest_end)
    ot_hours, ot_minutes, dropped_minutes = _calc_ot_hours(
        ot_start_dt, check_out_dt, ot_cutoff_dt, min_ot_minutes, granularity_minutes
    )
    
    cross_day_note = "（次日凌晨下班）" if check_out_dt.date() != record_date else ""
    cutoff_note = (
        f"（超出最晚加班截止 {ot_latest_end} 的 {dropped_minutes}分钟不计）"
        if dropped_minutes > 0 else ""
    )
    
    # 规则 4: 周内加班 (周一至周五)
    if not is_weekend:
        if ot_hours > 0:
            result["overtime_hours"] = ot_hours
            result["detail_type"] = "周内加班"
            result["notes"] = f"{weekday_ot_start}后延时加班 {ot_minutes}分钟，计 {ot_hours}小时{cross_day_note}{cutoff_note}"
        elif ot_minutes > 0:
            result["notes"] = f"{weekday_ot_start}后仅 {ot_minutes}分钟 (未满{min_ot_minutes}分钟起算线，不计){cross_day_note}{cutoff_note}"
        else:
            result["notes"] = f"{weekday_ot_start}前下班，无加班"
            
    # 规则 5: 周末加班 (周六/周日且非公休)
    else:
        if include_weekend_base:
            # 标准班次内有效出勤工时 (已排除 12:00-13:00 午休)
            base_weekend_hours = standard_work_hours(
                record_date, check_in_dt, check_out_dt,
                _parse_hhmm(weekday_standard_end, WORK_AFTERNOON_END)
            )
            result["overtime_hours"] = round(base_weekend_hours + ot_hours, 2)
            result["detail_type"] = "周末加班"
            result["notes"] = (
                f"周末出勤基础工时 {base_weekend_hours}h + {weekday_ot_start}后加班 {ot_hours}h"
                f"{cross_day_note}{cutoff_note}（注：未见HR审批单，按打卡出勤兜底）"
            )
        else:
            result["overtime_hours"] = 0.0
            result["detail_type"] = "公休" if is_public_holiday_shift else "正常工时"
            result["notes"] = "周末无有效加班审批单，不计入加班"
        
    return result


def calculate_overtime_allowance(total_hours: float) -> tuple:
    """
    根据月累计加班时长 (H) 计算加班津贴与对应等级
    阶梯规则:
    - 等级 1:  H ≤ 20 小时        -> ¥ 0
    - 等级 2:  20 < H ≤ 30 小时   -> ¥ 200
    - 等级 3:  30 < H ≤ 36 小时   -> ¥ 300
    - 等级 4:  36 < H ≤ 40 小时   -> ¥ 400
    - 等级 5:  40 < H ≤ 45 小时   -> ¥ 500
    - 等级 6:  45 < H ≤ 50 小时   -> ¥ 600
    - 等级 7:  50 < H ≤ 55 小时   -> ¥ 700
    - 等级 8:  55 < H ≤ 60 小时   -> ¥ 800
    - 等级 9:  60 < H ≤ 65 小时   -> ¥ 900
    - 等级 10: 65 < H ≤ 70 小时   -> ¥ 1000
    - 等级 11: 70 < H ≤ 75 小时   -> ¥ 1100
    - 等级 12: 75 < H ≤ 80 小时   -> ¥ 1200
    - 等级 13: 80 < H ≤ 85 小时   -> ¥ 1300
    - 等级 14: 85 < H ≤ 90 小时   -> ¥ 1400
    - 等级 15: H > 90 小时        -> ¥ 1500

    返回: (津贴金额: int, 等级名称: str, 区间描述: str)
    """
    h = round(float(total_hours), 2)
    if h <= 20:
        return 0, "等级 1", "H ≤ 20h"
    elif h <= 30:
        return 200, "等级 2", "20 < H ≤ 30h"
    elif h <= 36:
        return 300, "等级 3", "30 < H ≤ 36h"
    elif h <= 40:
        return 400, "等级 4", "36 < H ≤ 40h"
    elif h <= 45:
        return 500, "等级 5", "40 < H ≤ 45h"
    elif h <= 50:
        return 600, "等级 6", "45 < H ≤ 50h"
    elif h <= 55:
        return 700, "等级 7", "50 < H ≤ 55h"
    elif h <= 60:
        return 800, "等级 8", "55 < H ≤ 60h"
    elif h <= 65:
        return 900, "等级 9", "60 < H ≤ 65h"
    elif h <= 70:
        return 1000, "等级 10", "65 < H ≤ 70h"
    elif h <= 75:
        return 1100, "等级 11", "70 < H ≤ 75h"
    elif h <= 80:
        return 1200, "等级 12", "75 < H ≤ 80h"
    elif h <= 85:
        return 1300, "等级 13", "80 < H ≤ 85h"
    elif h <= 90:
        return 1400, "等级 14", "85 < H ≤ 90h"
    else:
        return 1500, "等级 15", "H > 90h"
