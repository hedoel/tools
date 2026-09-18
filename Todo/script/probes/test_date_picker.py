from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

options = Options()
options.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
service = webdriver.edge.service.Service(executable_path='../driver/msedgedriver.exe')
driver = webdriver.Edge(service=service, options=options)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if "attendance-overview" in driver.current_url:
        break

print("Target page URL:", driver.current_url)

range_inputs = driver.find_elements(By.CSS_SELECTOR, ".right-datepicker input.el-range-input")
print("Found range inputs:", len(range_inputs))

if len(range_inputs) >= 2:
    start_inp = range_inputs[0]
    end_inp = range_inputs[1]
    
    # 测试方案 A: 使用 JavaScript 派发真实键盘/输入事件
    js_code = """
    const startInp = arguments[0];
    const endInp = arguments[1];
    const startDate = arguments[2];
    const endDate = arguments[3];
    
    startInp.focus();
    startInp.value = startDate;
    startInp.dispatchEvent(new Event('input', { bubbles: true }));
    startInp.dispatchEvent(new Event('change', { bubbles: true }));
    
    endInp.focus();
    endInp.value = endDate;
    endInp.dispatchEvent(new Event('input', { bubbles: true }));
    endInp.dispatchEvent(new Event('change', { bubbles: true }));
    
    // 模拟 Enter 确认或者让 Vue 响应
    endInp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
    endInp.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', keyCode: 13, bubbles: true }));
    """
    driver.execute_script(js_code, start_inp, end_inp, "2026-05-01", "2026-05-31")
    time.sleep(1)
    
    print("Values after JS dispatch:")
    print("Start input value:", start_inp.get_attribute("value"))
    print("End input value:", end_inp.get_attribute("value"))
    
    # 查找是否有【确定】按钮在弹出的日历面板上
    confirm_btns = driver.find_elements(By.XPATH, "//button[contains(@class, 'el-picker-panel__link-btn') or contains(., '确定') or contains(., 'Confirm')]")
    for btn in confirm_btns:
        if btn.is_displayed():
            print("Found confirm button:", btn.text)
            btn.click()
            time.sleep(1)
            
    # 点击空白处或标题收起日历
    driver.execute_script("document.body.click();")
    time.sleep(2)
    print("Current URL:", driver.current_url)
