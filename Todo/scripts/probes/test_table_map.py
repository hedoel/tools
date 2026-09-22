from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
import re

options = Options()
options.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
service = webdriver.edge.service.Service(executable_path='../driver/msedgedriver.exe')
driver = webdriver.Edge(service=service, options=options)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if "attendance-overview" in driver.current_url:
        break

# 查看表头的日期
headers = driver.find_elements(By.CSS_SELECTOR, ".roster-table-header div, .roster-table-header span")
print("Found header items:", len(headers))
date_nums = []
for h in headers:
    t = h.text.strip()
    if re.fullmatch(r'\d{2}', t):
        date_nums.append(t)
print("Detected date numbers in header:", date_nums)

# 查看第一行员工的打卡单元格
cells = driver.find_elements(By.CSS_SELECTOR, ".drag-selector-item.body-td-datetime")
print("Total cells in row:", len(cells))
