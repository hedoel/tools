from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time
import re

options = Options()
options.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
service = webdriver.edge.service.Service(executable_path='../driver/msedgedriver.exe')
driver = webdriver.Edge(service=service, options=options)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if "attendance-overview" in driver.current_url:
        break

# 确保关闭之前可能存在的抽屉
driver.execute_script("""
    const closeBtn = document.querySelector('.er-dialog-close');
    if (closeBtn) closeBtn.click();
""")
time.sleep(0.5)

cells = driver.find_elements(By.CSS_SELECTOR, ".drag-selector-item.body-td-datetime")
print("Total cells for 9月:", len(cells))

# 点击第一天 (09-01)
c1 = cells[0]
driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", c1)
time.sleep(0.3)
inners = c1.find_elements(By.CSS_SELECTOR, ".date-cell-clock-item, .date-cell")
target = inners[0] if inners else c1
driver.execute_script("arguments[0].click();", target)
time.sleep(1.5)

# 提取日结详情
title = "-"
shift = "-"
cin = "-"
cout = "-"

titles = driver.find_elements(By.XPATH, "//*[contains(text(), '日结详情')]")
if titles:
    title = titles[0].text.replace('\n', ' ')

shift_els = driver.find_elements(By.XPATH, "//*[contains(text(), '考勤班次')]")
if shift_els:
    parent = shift_els[0].find_element(By.XPATH, "..")
    shift = parent.text.replace("考勤班次", "").strip()

in_els = driver.find_elements(By.XPATH, "//*[contains(text(), '上班打卡时间')]")
for el in in_els:
    parent = el.find_element(By.XPATH, "..")
    txt = parent.text.replace("上班打卡时间", "").strip()
    m = re.search(r'\d{2}-\d{2}\s+\d{2}:\d{2}', txt)
    if m:
        cin = m.group(0)
        break

out_els = driver.find_elements(By.XPATH, "//*[contains(text(), '下班打卡时间')]")
for el in out_els:
    parent = el.find_element(By.XPATH, "..")
    txt = parent.text.replace("下班打卡时间", "").strip()
    m = re.search(r'\d{2}-\d{2}\s+\d{2}:\d{2}', txt)
    if m:
        cout = m.group(0)
        break

print(f"Result -> Title: {title} | Shift: {shift} | In: {cin} | Out: {cout}")
