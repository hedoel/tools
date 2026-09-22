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

# 先把日期下拉框通过点击空白处收起
driver.execute_script("document.body.click();")
time.sleep(1)

# 找到所有的打卡单元格
cells = driver.find_elements(By.CSS_SELECTOR, ".drag-selector-item.body-td-datetime")
print("Total cells found:", len(cells))

if cells:
    target_cell = cells[0]
    print("Clicking first cell...")
    # 使用 JavaScript 点击以防遮挡
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_cell)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", target_cell)
    time.sleep(2)
    
    # 查找抽屉或日结详情
    print("\n--- Looking for Day Detail Drawer ---")
    drawers = driver.find_elements(By.XPATH, "//*[contains(text(), '日结详情') or contains(text(), '考勤班次')]")
    for d in drawers:
        print("Found element:", d.tag_name, d.get_attribute("class"), repr(d.text[:80]))
        
    # 查看上班打卡时间与下班打卡时间
    in_outs = driver.find_elements(By.XPATH, "//*[contains(text(), '打卡时间')]")
    for io in in_outs:
        parent = io.find_element(By.XPATH, "..")
        print("Punch time element parent text:", repr(parent.text))
