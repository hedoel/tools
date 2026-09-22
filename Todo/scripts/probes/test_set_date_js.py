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

# 测试通过 JavaScript 设置日期并触发 Vue 响应
set_date_js = """
const rangeEditor = document.querySelector('.right-datepicker');
if (!rangeEditor) return 'No range editor';
const inputs = rangeEditor.querySelectorAll('input.el-range-input');
if (inputs.length < 2) return 'Not enough inputs';

const startInp = inputs[0];
const endInp = inputs[1];

startInp.focus();
startInp.value = arguments[0];
startInp.dispatchEvent(new Event('input', { bubbles: true }));
startInp.dispatchEvent(new Event('change', { bubbles: true }));

endInp.focus();
endInp.value = arguments[1];
endInp.dispatchEvent(new Event('input', { bubbles: true }));
endInp.dispatchEvent(new Event('change', { bubbles: true }));

endInp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
endInp.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', keyCode: 13, bubbles: true }));

// 关闭弹窗
document.body.click();
return 'OK: ' + startInp.value + ' ~ ' + endInp.value;
"""

res = driver.execute_script(set_date_js, "2026-09-01", "2026-09-30")
print("JS Execution:", res)
time.sleep(2)

# 检查当前页面的单元格
cells = driver.find_elements(By.CSS_SELECTOR, ".drag-selector-item.body-td-datetime")
print(f"Cells count after date change: {len(cells)}")

# 检查日期输入框当前的显示值
range_inputs = driver.find_elements(By.CSS_SELECTOR, ".right-datepicker input.el-range-input")
for i, inp in enumerate(range_inputs):
    print(f"Range input {i}: {inp.get_attribute('value')}")
