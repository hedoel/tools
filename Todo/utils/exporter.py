import os
from datetime import datetime
from typing import List, Dict, Any
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

def export_overtime_to_excel(
    records: List[Dict[str, Any]],
    emp_id: str,
    emp_name: str,
    date_range_str: str,
    output_path: str
) -> str:
    """
    使用 openpyxl 导出格式优美的考勤与加班时长明细报表
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "加班时长统计明细"
    ws.views.sheetView[0].showGridLines = True
    
    # 样式定义
    font_title = Font(name="微软雅黑", size=16, bold=True, color="1F4E79")
    font_sub = Font(name="微软雅黑", size=10, color="595959")
    font_header = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    font_cell = Font(name="微软雅黑", size=10)
    font_total = Font(name="微软雅黑", size=11, bold=True, color="C00000")
    
    fill_header = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    fill_overtime = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid") # 浅绿
    fill_weekend = PatternFill(start_color="EDF2F8", end_color="EDF2F8", fill_type="solid")  # 浅蓝
    fill_holiday = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")  # 浅灰
    fill_total = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")    # 浅黄
    
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')
    
    # 1. 主标题
    ws.merge_cells("A1:I1")
    ws["A1"] = "考勤打卡与加班时长核算报表"
    ws["A1"].font = font_title
    ws["A1"].alignment = align_center
    ws.row_dimensions[1].height = 40
    
    # 2. 基础信息副标题
    ws.merge_cells("A2:I2")
    ws["A2"] = f"员工工号: {emp_id}    员工姓名: {emp_name}    核算区间: {date_range_str}    生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ws["A2"].font = font_sub
    ws["A2"].alignment = align_center
    ws.row_dimensions[2].height = 24
    
    # 3. 数据表头
    headers = [
        "序号", "日期", "星期", "考勤班次", 
        "上班打卡", "下班打卡", "核算类别", "加班时长 (小时)", "计算备注说明"
    ]
    start_row = 4
    ws.row_dimensions[start_row].height = 28
    
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=header)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
        
    # 4. 写入数据行
    current_row = start_row + 1
    total_ot = 0.0
    
    for idx, r in enumerate(records, start=1):
        ws.row_dimensions[current_row].height = 22
        ot_hours = float(r.get("overtime_hours", 0.0))
        total_ot += ot_hours
        
        row_vals = [
            idx,
            r.get("date", ""),
            r.get("weekday", ""),
            r.get("shift_name", ""),
            r.get("check_in", "-"),
            r.get("check_out", "-"),
            r.get("detail_type", ""),
            ot_hours,
            r.get("notes", "")
        ]
        
        # 判断底色
        row_fill = None
        if r.get("is_public_holiday", False):
            row_fill = fill_holiday
        elif ot_hours > 0:
            row_fill = fill_overtime
        elif r.get("is_weekend", False) and not r.get("is_substitute_workday", False):
            row_fill = fill_weekend
            
        for col_idx, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = font_cell
            cell.border = thin_border
            if row_fill:
                cell.fill = row_fill
                
            if col_idx in [1, 2, 3, 5, 6, 7]:
                cell.alignment = align_center
            elif col_idx == 8:
                cell.alignment = align_right
                cell.number_format = '0.0'
            else:
                cell.alignment = align_left
                
        current_row += 1
        
    # 5. 汇总行
    ws.row_dimensions[current_row].height = 26
    ws.cell(row=current_row, column=1, value="合计").font = font_total
    ws.cell(row=current_row, column=1).alignment = align_center
    ws.cell(row=current_row, column=1).fill = fill_total
    ws.cell(row=current_row, column=1).border = thin_border
    
    for c in range(2, 8):
        cell = ws.cell(row=current_row, column=c, value="")
        cell.fill = fill_total
        cell.border = thin_border
        
    from core.calculator import calculate_overtime_allowance
    allowance, level_name, _ = calculate_overtime_allowance(total_ot)
    
    formula_cell = ws.cell(row=current_row, column=8)
    formula_cell.value = f"=SUM(H{start_row+1}:H{current_row-1})"
    formula_cell.font = font_total
    formula_cell.fill = fill_total
    formula_cell.border = thin_border
    formula_cell.alignment = align_right
    formula_cell.number_format = '0.0'
    
    note_cell = ws.cell(row=current_row, column=9, value=f"共累计有效加班: {round(total_ot, 1)}h | 加班津贴: {allowance}元 ({level_name})")
    note_cell.font = font_total
    note_cell.fill = fill_total
    note_cell.border = thin_border
    note_cell.alignment = align_left
    
    # 6. 自适应列宽
    col_widths = {1: 8, 2: 14, 3: 10, 4: 28, 5: 16, 6: 16, 7: 14, 8: 18, 9: 45}
    for col_idx, width in col_widths.items():
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width
        
    wb.save(output_path)
    return output_path
