import os
import sys
import time
import json
import shutil
import socket
import subprocess
import tempfile
import urllib.request
from typing import Tuple, Optional
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import selenium.webdriver.edge.webdriver
import selenium.webdriver.chromium.webdriver
import selenium.webdriver.remote.webdriver


def find_edge_binary(custom_path: Optional[str] = None) -> str:
    """
    智能动态探测系统安装的 Microsoft Edge 浏览器路径 (B4)
    支持: 用户配置路径、注册表 App Paths、Program Files (64位/32位)、LocalAppData、系统 PATH
    """
    if custom_path and os.path.exists(custom_path):
        return custom_path

    # 1. 尝试读取 Windows 注册表 App Paths
    if sys.platform == "win32":
        try:
            import winreg
            for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    with winreg.OpenKey(
                        root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"
                    ) as key:
                        val, _ = winreg.QueryValueEx(key, "")
                        if val and os.path.exists(val):
                            return val
                except OSError:
                    pass
        except ImportError:
            pass

    # 2. 尝试常见系统安装目录
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_appdata = os.environ.get("LocalAppData", "")

    candidates = [
        os.path.join(prog_files, r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(prog_files_x86, r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(local_appdata, r"Microsoft\Edge\Application\msedge.exe") if local_appdata else "",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p

    # 3. 尝试 PATH 环境变量
    which_path = shutil.which("msedge") or shutil.which("msedge.exe")
    if which_path and os.path.exists(which_path):
        return which_path

    # 若均未找到，抛出友好中文异常
    raise FileNotFoundError(
        "未在当前系统中检测到 Microsoft Edge 浏览器 (msedge.exe)。\n"
        "请确认已安装 Edge 浏览器，或将其实际安装路径添加到系统环境变量 PATH 中。"
    )


def clean_stale_profiles(prefix: str = "edge_hr_profile_", max_age_seconds: int = 86400):
    """
    启动前扫描并清理 %TEMP% 目录下残留超过指定时长的临时 profile 目录 (B3)
    默认清理超过 24 小时的孤儿目录，防止进程异常退出或强杀导致磁盘泄漏
    """
    try:
        temp_base = tempfile.gettempdir()
        now = time.time()
        for name in os.listdir(temp_base):
            if name.startswith(prefix):
                full_path = os.path.join(temp_base, name)
                if os.path.isdir(full_path):
                    try:
                        mtime = os.path.getmtime(full_path)
                        if now - mtime > max_age_seconds:
                            shutil.rmtree(full_path, ignore_errors=True)
                    except Exception:
                        pass
    except Exception:
        pass


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
    def __init__(self, port: Optional[int] = None, headless: bool = True, edge_bin: Optional[str] = None):
        # B2: 若未指定固定端口，则自动分配空闲端口，避免与用户本地开发环境冲突
        if port is None or port <= 0:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', 0))
                self.port = s.getsockname()[1]
            self.is_custom_port = False
        else:
            self.port = port
            self.is_custom_port = True

        self.headless = headless
        self.edge_bin = edge_bin
        self.proc: Optional[subprocess.Popen] = None
        self.driver: Optional[webdriver.Edge] = None
        self.temp_dir: Optional[str] = None
        # B1: 标记浏览器是否由本实例自启动 (若连接用户自有浏览器则禁止退出时强杀)
        self.is_self_launched: bool = False
        
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
        # B3: 启动前自动打扫历史残留的过期临时 profile
        clean_stale_profiles()

        # B4: 动态探测 Edge 浏览器执行文件 (优先使用传入的自定义/配置路径)
        edge_bin = find_edge_binary(self.edge_bin)

        # 检查指定端口是否已有存活的 Edge 调试实例
        if self._is_port_alive():
            # B1: 端口已存活说明是复用现有实例，绝不可在退出时杀掉用户自有浏览器
            self.is_self_launched = False
        else:
            self.is_self_launched = True
            self.temp_dir = tempfile.mkdtemp(prefix="edge_hr_profile_")
            cmd = [
                edge_bin,
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
        
        driver_path = get_driver_path()
        service = Service(executable_path=driver_path)
        if sys.platform == "win32":
            service.creation_flags = subprocess.CREATE_NO_WINDOW
            
        try:
            self.driver = webdriver.Edge(service=service, options=options)
        except Exception as e:
            # B5: 捕获驱动与 Edge 版本失配，尝试回退自动驱动或给出清晰易懂的中文指导
            err_str = str(e)
            fallback_success = False
            if "version" in err_str.lower() or "session not created" in err_str.lower():
                try:
                    # 尝试不指定路径回退使用 Selenium Manager 自动匹配
                    fallback_service = Service()
                    if sys.platform == "win32":
                        fallback_service.creation_flags = subprocess.CREATE_NO_WINDOW
                    self.driver = webdriver.Edge(service=fallback_service, options=options)
                    fallback_success = True
                except Exception:
                    fallback_success = False

            if not fallback_success:
                if "version" in err_str.lower() or "session not created" in err_str.lower():
                    raise RuntimeError(
                        f"Edge 浏览器版本与随包驱动不匹配！\n"
                        f"错误详情: {err_str}\n"
                        f"解决建议: 您的 Edge 浏览器近期可能已自动升级，请下载与当前 Edge 版本匹配的 msedgedriver.exe 覆盖至 driver 目录。"
                    ) from e
                raise

        # 隐式等待必须保持为 0：等待统一由 scraper 的显式等待负责
        self.driver.implicitly_wait(0)
        try:
            self.driver.set_window_size(1920, 1080)
        except Exception:
            pass
        return self.driver
        
    def quit(self):
        """
        释放驱动、浏览器进程与临时缓存目录
        B1 核心保障: 若是复用用户自己打开的 Edge，仅释放连接，绝不关闭用户浏览器或强杀进程！
        """
        if self.driver:
            try:
                if self.is_self_launched:
                    self.driver.quit()
                else:
                    # 外部复用的浏览器仅关闭采集所用的当前标签页
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
            except Exception:
                pass
            self.driver = None
            
        if self.proc:
            if self.is_self_launched:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=2)
                except Exception:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
            self.proc = None
            
        # 清理本次运行生成的临时用户目录
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass
            self.temp_dir = None

