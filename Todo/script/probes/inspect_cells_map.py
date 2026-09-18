from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

options = Options()
options.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
service = webdriver.edge.service.Service(executable_path='../driver/msedgedriver.exe')
driver = webdriver.Edge(service=service, options=options)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if "attendance-overview" in driver.current_url:
        break

print("Page URL:", driver.current_url)

# 检查所有日历单元格及其属性、包含的文本
cells = driver.find_elements(By.CSS_SELECTOR, ".drag-selector-item.body-td-datetime")
print(f"Total .drag-selector-item.body-td-datetime found: {len(cells)}")

for idx, c in enumerate(cells[:15]):
    # 获取此单元格关联的日期信息（如属性、父节点、或同列表头）
    attrs = driver.execute_script('''
        const el = arguments[0];
        const res = {};
        for (let a of el.attributes) {
            res[a.name] = a.value;
        }
        // 查看是否有 data-date 或其它标识
        res['_innerText'] = el.innerText ? el.innerText.trim().replace(/\\n/g, ' ') : '';
        return res;
    ''', c)
    print(f"Cell {idx}: {attrs}")
