from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
import time

options = Options()
options.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
service = webdriver.edge.service.Service(executable_path='../driver/msedgedriver.exe')
driver = webdriver.Edge(service=service, options=options)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if "attendance-overview" in driver.current_url:
        break

# 1. 检查日期选择器内部和外部
print("--- Check Date Picker ---")
picker_wrapper = driver.find_element(By.CSS_SELECTOR, ".right-datepicker")
print("Picker wrapper class:", picker_wrapper.get_attribute("class"))

# 2. 检查日历表格的表头与单元格
print("\n--- Check Attendance Overview Table Header ---")
# 找到表头的所有日期列 (例如 18, 19, 20... 或 01, 02, 03...)
headers = driver.find_elements(By.XPATH, "//div[contains(@class, 'header') or contains(@class, 'th') or contains(@class, 'col')]")
for h in headers:
    t = h.text.strip()
    if any(x in t for x in ["01", "02", "18", "19", "周", "一", "二", "三"]):
        print(f"Header: tag={h.tag_name}, class='{h.get_attribute('class')}', text='{repr(t)}'")

print("\n--- Check Daily Attendance Cells ---")
# 找出第一行员工的每一天单元格
date_cells = driver.find_elements(By.CSS_SELECTOR, ".drag-selector-item, .date-cell")
print(f"Found {len(date_cells)} date cells")
for idx, dc in enumerate(date_cells[:10]):
    print(f"Cell {idx}: class='{dc.get_attribute('class')}', text='{repr(dc.text.replace(chr(10), ' '))}'")
