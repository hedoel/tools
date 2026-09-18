from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

options = Options()
options.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
service = webdriver.edge.service.Service(executable_path='../driver/msedgedriver.exe')
driver = webdriver.Edge(service=service, options=options)

print("Open tabs count:", len(driver.window_handles))
target_handle = None
for h in driver.window_handles:
    driver.switch_to.window(h)
    print("Tab URL:", driver.current_url, "Title:", driver.title)
    if "attendance-overview" in driver.current_url:
        target_handle = h

if target_handle:
    driver.switch_to.window(target_handle)
    print("\n--- On Attendance Overview Page ---")
    
    # 查找所有 input
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for idx, inp in enumerate(inputs):
        cls = inp.get_attribute("class") or ""
        ph = inp.get_attribute("placeholder") or ""
        val = inp.get_attribute("value") or ""
        print(f"Input {idx}: tag={inp.tag_name}, class='{cls}', placeholder='{ph}', value='{val}'")
        
    # 查找日期选择器外层容器
    print("\n--- Date Picker Containers ---")
    containers = driver.find_elements(By.XPATH, "//*[contains(@class, 'range') or contains(@class, 'date')]")
    for c in containers[:15]:
        cls = c.get_attribute("class") or ""
        if "picker" in cls or "date" in cls or "range" in cls:
            print(f"Container tag={c.tag_name}, class='{cls}', text='{c.text.strip()[:60]}'")
            
    # 查找表格中的单元格结构
    print("\n--- Calendar Cells Sample ---")
    cells = driver.find_elements(By.XPATH, "//div[contains(., 'SD3') or contains(., '考勤')]")
    print(f"Found {len(cells)} cells with SD3/考勤")
    for c in cells[:5]:
        if c.is_displayed():
            print(f"Cell tag={c.tag_name}, class='{c.get_attribute('class')}', text='{c.text.replace(chr(10), ' ')}'")
