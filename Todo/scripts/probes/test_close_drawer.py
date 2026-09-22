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

# 查找关闭按钮
close_candidates = driver.find_elements(By.CSS_SELECTOR, ".el-icon-d-arrow-left, .el-icon-d-arrow-right, .el-drawer__close-btn, .close, [class*='arrow-right'], [class*='arrow-left']")
print("Close candidates:", len(close_candidates))
for c in close_candidates:
    if c.is_displayed():
        print("Candidate:", c.tag_name, c.get_attribute("class"))
        c.click()
        time.sleep(1)
        break

# 或者查看标题旁边的按钮
title_icons = driver.find_elements(By.XPATH, "//*[contains(text(), '日结详情')]/preceding-sibling::* | //*[contains(text(), '日结详情')]/parent::*//*[contains(@class, 'icon') or contains(@class, 'btn')]")
print("Title icons:", len(title_icons))
for ti in title_icons:
    if ti.is_displayed():
        print("Clicking title icon:", ti.get_attribute("class"))
        ti.click()
        time.sleep(1)
        break

# 检查抽屉是否已关闭
drawers = driver.find_elements(By.XPATH, "//*[contains(text(), '日结详情')]")
print("Drawers displayed after close:", any(d.is_displayed() for d in drawers))
