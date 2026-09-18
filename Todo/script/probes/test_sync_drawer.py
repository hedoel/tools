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

def click_and_read_day(date_str):
    print(f"\n--- Testing click for date: {date_str} ---")
    # 查找精准对应的单元格
    cell = driver.find_elements(By.CSS_SELECTOR, f"div[customattribute*='\"prop\":\"{date_str}\"']")
    if not cell:
        print("Cell not found!")
        return
        
    c = cell[0]
    # 滚动到中心并点击
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", c)
    time.sleep(0.3)
    
    inners = c.find_elements(By.CSS_SELECTOR, ".date-cell-clock-item, .date-cell")
    target = inners[0] if inners else c
    driver.execute_script("arguments[0].click();", target)
    
    # 等待抽屉标题更新为目标日期
    formatted_date = date_str.replace('-', '/')  # 2026/09/02
    start_wait = time.time()
    drawer_date_found = False
    
    for _ in range(20):
        titles = driver.find_elements(By.CSS_SELECTOR, ".attendance-day-end-audit-title .title-left")
        for t in titles:
            if t.is_displayed() and formatted_date in t.text:
                drawer_date_found = True
                print(f"Drawer updated to {formatted_date} in {time.time() - start_wait:.2f}s!")
                break
        if drawer_date_found:
            break
        time.sleep(0.2)
        
    if not drawer_date_found:
        print(f"Warning: Drawer title did not match {formatted_date}!")
        titles = driver.find_elements(By.CSS_SELECTOR, ".attendance-day-end-audit-title .title-left")
        for t in titles:
            if t.is_displayed():
                print("Current drawer title:", t.text)

    # 打印该抽屉中当天的打卡时间
    warp = driver.find_element(By.CSS_SELECTOR, ".er-dialog-warp")
    txt = warp.text
    print("Drawer content preview:")
    for line in txt.split('\n'):
        if any(k in line for k in ['打卡时间', '考勤班次', '应出勤时长', '有效加班']):
            print("  ", line)

# 测试连续点击 09-01, 09-02, 09-03
click_and_read_day("2026-09-01")
click_and_read_day("2026-09-02")
click_and_read_day("2026-09-03")
click_and_read_day("2026-09-04")
