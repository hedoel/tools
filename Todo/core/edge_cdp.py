import os
import sys
import time
import json
import shutil
import subprocess
import tempfile
import urllib.request
from typing import Tuple, Optional
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

DEFAULT_EDGE_BIN = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def get_driver_path() -> str:
    """动态获取 msedgedriver.exe 路径，完美兼容 PyInstaller 打包前后"""
    # 1. 如果是 PyInstaller 打包环境
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        p1 = os.path.join(exe_dir, "driver", "msedgedriver.exe")
        if os.path.exists(p1):
            return p1
        p2 = os.path.join(exe_dir, "msedgedriver.exe")
        if os.path.exists(p2):
            return p2
        p3 = os.path.join(exe_dir, "_internal", "driver", "msedgedriver.exe")
        if os.path.exists(p3):
            return p3
        mei_dir = getattr(sys, '_MEIPASS', '')
        p4 = os.path.join(mei_dir, "driver", "msedgedriver.exe")
        if os.path.exists(p4):
            return p4
            
    # 2. 源码开发环境
    candidates = [
        os.path.abspath("driver/msedgedriver.exe"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "driver", "msedgedriver.exe")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "msedgedriver.exe"

DRIVER_PATH = get_driver_path()

class EdgeCDPManager:
    def __init__(self, port: int = 9222, headless: bool = True):
        self.port = port
        self.headless = headless
        self.proc: Optional[subprocess.Popen] = None
        self.driver: Optional[webdriver.Edge] = None
        self.temp_dir: Optional[str] = None
        
    def _is_port_alive(self) -> bool:
        try:
            url = f"http://127.0.0.1:{self.port}/json/version"
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            return False
        return False
        
    def start(self, initial_url: str = "https://www.eveportal.com/login") -> webdriver.Edge:
        """启动 Edge 并通过 CDP 连接 Selenium"""
        if not self._is_port_alive():
            self.temp_dir = tempfile.mkdtemp(prefix="edge_hr_profile_")
            cmd = [
                DEFAULT_EDGE_BIN,
                f"--user-data-dir={self.temp_dir}",
                f"--remote-debugging-port={self.port}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                "--disable-sync",
                "--window-size=1920,1080",
                initial_url
            ]
            if self.headless:
                cmd.extend([
                    "--headless=new",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--disable-blink-features=AutomationControlled"
                ])
                
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
                
            self.proc = subprocess.Popen(cmd, creationflags=creationflags)
            
            # 等待端口就绪
            start_t = time.time()
            alive = False
            while time.time() - start_t < 12:
                if self._is_port_alive():
                    alive = True
                    break
                time.sleep(0.5)
                
            if not alive:
                raise RuntimeError(f"Edge 浏览器无法在端口 {self.port} 启动调试服务")
                
        # 连接 Selenium
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.port}")
        
        service = Service(executable_path=get_driver_path())
        if sys.platform == "win32":
            service.creation_flags = subprocess.CREATE_NO_WINDOW
            
        self.driver = webdriver.Edge(service=service, options=options)
        # 隐式等待必须保持为 0：它会让所有“找不到元素”的 find_elements 阻塞满超时时间，
        # 与页面里成批的候选选择器叠加后会白等数分钟。等待统一由 scraper 的显式等待负责。
        self.driver.implicitly_wait(0)
        try:
            self.driver.set_window_size(1920, 1080)
        except Exception:
            pass
        return self.driver
        
    def quit(self):
        """彻底释放驱动、浏览器进程与临时缓存目录"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
            
        # 清理用户临时数据目录，释放磁盘空间与缓存
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass
            self.temp_dir = None
