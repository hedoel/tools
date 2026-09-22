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

# 提取日结详情
headers = driver.find_elements(By.XPATH, "//*[contains(text(), '日结详情')]")
if headers:
    title_text = headers[0].text
    print("Found Title:", title_text)
    
# 查找班次
shift_name = "-"
shift_els = driver.find_elements(By.XPATH, "//*[contains(text(), '考勤班次')]")
if shift_els:
    parent = shift_els[0].find_element(By.XPATH, "..")
    shift_name = parent.text.replace("考勤班次", "").strip()
print("Parsed Shift:", shift_name)

# 查找上下班打卡时间
check_in = "-"
check_out = "-"
in_els = driver.find_elements(By.XPATH, "//*[contains(text(), '上班打卡时间')]")
if in_els:
    parent = in_els[0].find_element(By.XPATH, "..")
    txt = parent.text.replace("上班打卡时间", "").strip()
    m = re.search(r'\d{2}-\d{2}\s+\d{2}:\d{2}', txt)
    if m:
        check_in = m.group(0)
    else:
        check_in = txt
print("Parsed Check-In:", check_in)

out_els = driver.find_elements(By.XPATH, "//*[contains(text(), '下班打卡时间')]")
if out_els:
    parent = out_els[0].find_element(By.XPATH, "..")
    txt = parent.text.replace("下班打卡时间", "").strip()
    m = re.search(r'\d{2}-\d{2}\s+\d{2}:\d{2}', txt)
    if m:
        check_out = m.group(0)
    else:
        check_out = txt
print("Parsed Check-Out:", check_out)
