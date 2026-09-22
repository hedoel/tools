from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time

options = Options()
options.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
service = webdriver.edge.service.Service(executable_path='../driver/msedgedriver.exe')
driver = webdriver.Edge(service=service, options=options)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if "attendance-overview" in driver.current_url:
        break

cells = driver.find_elements(By.CSS_SELECTOR, ".drag-selector-item.body-td-datetime")
print(f"Testing iteration over first 3 cells out of {len(cells)}...")

for i in range(min(3, len(cells))):
    c = cells[i]
    driver.execute_script("arguments[0].scrollIntoView({inline: 'center', block: 'center'});", c)
    time.sleep(0.3)
    
    # 查找内部可点击元素
    inners = c.find_elements(By.CSS_SELECTOR, ".date-cell-clock-item, .date-cell")
    target = inners[0] if inners else c
    
    try:
        ActionChains(driver).move_to_element(target).click().perform()
    except Exception:
        driver.execute_script("arguments[0].click();", target)
        
    time.sleep(1)
    
    # 读取抽屉顶部标题
    title_els = driver.find_elements(By.XPATH, "//*[contains(text(), '日结详情')]")
    t_text = title_els[0].text if title_els else "No title"
    print(f"Cell {i} clicked -> Drawer header: {t_text}")
