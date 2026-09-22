from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
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

def scrape_day(year, month, day):
    target_date_str = f"{year:04d}-{month:02d}-{day:02d}"
    target_slash = f"{year:04d}/{month:02d}/{day:02d}"
    
    # 查找精准单元格
    cell_els = driver.find_elements(By.CSS_SELECTOR, f"div[customattribute*='\"prop\":\"{target_date_str}\"']")
    if not cell_els:
        return "-", "-", "-"
        
    c = cell_els[0]
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", c)
    time.sleep(0.15)
    
    inners = c.find_elements(By.CSS_SELECTOR, ".date-cell-clock-item, .date-cell")
    target = inners[0] if inners else c
    driver.execute_script("arguments[0].click();", target)
    
    # 等待抽屉标题更新到目标日期
    for _ in range(15):
        titles = driver.find_elements(By.CSS_SELECTOR, ".attendance-day-end-audit-title .title-left")
        if titles and titles[0].is_displayed() and target_slash in titles[0].text:
            break
        time.sleep(0.15)
        
    # 读取抽屉内容
    warp = driver.find_element(By.CSS_SELECTOR, ".er-dialog-warp")
    lines = [l.strip() for l in warp.text.split('\n') if l.strip()]
    
    shift = "白班"
    cin = "-"
    cout = "-"
    
    for i, line in enumerate(lines):
        if "考勤班次" in line:
            s = line.replace("考勤班次", "").strip()
            if not s and i + 1 < len(lines):
                s = lines[i+1]
            if s:
                shift = s
        elif "上班打卡时间" in line:
            if i + 1 < len(lines):
                val = lines[i+1]
                if re.search(r'\d{2}-\d{2}\s+\d{2}:\d{2}', val) or val == '-':
                    cin = val
        elif "下班打卡时间" in line:
            if i + 1 < len(lines):
                val = lines[i+1]
                if re.search(r'\d{2}-\d{2}\s+\d{2}:\d{2}', val) or val == '-':
                    cout = val
                    
    return shift, cin, cout

print("Testing first 7 days of 9月:")
for d in range(1, 8):
    shift, cin, cout = scrape_day(2026, 9, d)
    print(f"2026-09-{d:02d} -> Shift: {shift} | In: {cin} | Out: {cout}")
