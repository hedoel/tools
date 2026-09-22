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

headers = driver.find_elements(By.XPATH, "//*[contains(text(), '日结详情')]/parent::*")
if headers:
    print("Header outer HTML:\n", headers[0].get_attribute("outerHTML"))
