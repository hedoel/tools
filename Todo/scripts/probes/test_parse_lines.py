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

warp = driver.find_element(By.CSS_SELECTOR, ".er-dialog-warp")

print("--- Check-in / Check-out Lines ---")
# 找出所有包含时间打卡的文本
lines = warp.text.split('\n')
for i, line in enumerate(lines):
    if any(k in line for k in ['打卡时间', '上班', '下班', '考勤结果']):
        print(f"Line {i}: {line}")
        
# 检查精确的提取正则
cin = "-"
cout = "-"

# 匹配如: 上班打卡时间 09-01 08:18 或 09-02 08:23
for line in lines:
    if "上班打卡时间" in line:
        m = re.search(r'\d{2}-\d{2}\s+\d{2}:\d{2}', line)
        if m:
            cin = m.group(0)
    elif "下班打卡时间" in line:
        m = re.search(r'\d{2}-\d{2}\s+\d{2}:\d{2}', line)
        if m:
            cout = m.group(0)

print(f"Extracted -> In: {cin} | Out: {cout}")
