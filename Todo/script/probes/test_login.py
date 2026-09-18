import os
import time
import subprocess
import tempfile
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

temp_dir = tempfile.mkdtemp(prefix='edge_dev_')
edge_bin = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
cmd = [
    edge_bin,
    f"--user-data-dir={temp_dir}",
    "--remote-debugging-port=9222",
    "--no-first-run",
    "--no-default-browser-check",
    "https://www.eveportal.com/login"
]
proc = subprocess.Popen(cmd)
time.sleep(3)

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
service = Service(executable_path=os.path.abspath('../driver/msedgedriver.exe'))

try:
    driver = webdriver.Edge(service=service, options=options)
    print("CONNECTED SUCCESSFULLY! Page title:", driver.title)
    time.sleep(2)
    
    inputs = driver.find_elements(By.TAG_NAME, 'input')
    for i, inp in enumerate(inputs):
        print(f"Input {i}: type={inp.get_attribute('type')}, placeholder={inp.get_attribute('placeholder')}, id={inp.get_attribute('id')}, name={inp.get_attribute('name')}, class={inp.get_attribute('class')}")
        
    buttons = driver.find_elements(By.TAG_NAME, 'button')
    for i, btn in enumerate(buttons):
        print(f"Button {i}: text='{btn.text.strip()}', id={btn.get_attribute('id')}, class={btn.get_attribute('class')}")
        
    # Also find all clickable elements or text
    print("\nLooking for login button or form:")
    login_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '登录')]")
    for b in login_btns:
        print(f"Login element tag={b.tag_name}, text='{b.text}', class={b.get_attribute('class')}")
        
except Exception as e:
    print("Error during test:", e)
finally:
    try:
        driver.quit()
    except:
        pass
    proc.terminate()
