import os
import sys
import time
import json
import shutil
import socket
import subprocess
import tempfile
import urllib.request
from typing import Tuple, Optional, Callable
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


def get_edge_version(edge_bin: Optional[str] = None) -> Tuple[Optional[int], Optional[str]]:
    """读取本地 Edge 的主版本与完整版本 (如 152, '152.0.4191.53')"""
    if not edge_bin:
        try:
            edge_bin = find_edge_binary()
        except Exception:
            return None, None
    if not edge_bin or not os.path.exists(edge_bin):
        return None, None
    try:
        import win32api
        info = win32api.GetFileVersionInfo(edge_bin, '\\')
        ms = info['ProductVersionMS']
        ls = info['ProductVersionLS']
        major = ms >> 16
        full = f"{major}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
        return major, full
    except Exception:
        pass
    return None, None


def get_driver_path(edge_bin: Optional[str] = None) -> Optional[str]:
    major, _ = get_edge_version(edge_bin)

    # 候选驱动文件名按优先级排列
    filenames = []
    if major:
        filenames.append(f"msedgedriver_{major}.exe")
    filenames.extend(["msedgedriver.exe", "msedgedriver_152.exe", "msedgedriver_153.exe"])

    # 查找目录列表
    search_dirs = []
    # 优先检查用户 AppData 目录下的动态驱动缓存
    appdata_dir = os.path.join(os.environ.get("APPDATA", ""), "NoOvertime", "driver")
    if os.path.exists(appdata_dir):
        search_dirs.append(appdata_dir)

    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        search_dirs.extend([
            os.path.join(exe_dir, "driver"),
            exe_dir,
            os.path.join(exe_dir, "_internal", "driver"),
            os.path.join(getattr(sys, '_MEIPASS', ''), "driver")
        ])
    else:
        search_dirs.extend([
            os.path.abspath("driver"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "driver"),
            os.getcwd()
        ])

    for fname in filenames:
        for sdir in search_dirs:
            if not sdir:
                continue
            cand = os.path.join(sdir, fname)
            if os.path.exists(cand) and os.path.getsize(cand) > 0:
                return cand

    which_path = shutil.which("msedgedriver.exe") or shutil.which("msedgedriver")
    if which_path and os.path.exists(which_path) and os.path.getsize(which_path) > 0:
        return which_path

    return None


DRIVER_PATH: Optional[str] = get_driver_path()


class EdgeCDPManager:
    def __init__(
        self,
        port: Optional[int] = None,
        headless: bool = True,
        edge_bin: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ):
        self.progress = progress_callback or (lambda msg, pct: None)
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

    def _download_matching_driver(
        self, edge_major: Optional[int], edge_full_ver: Optional[str]
    ) -> Optional[str]:
        """
        从微软官方源动态下载与当前 Edge 版本匹配的 msedgedriver
        返回下载并解压后的驱动 exe 路径，失败返回 None
        """
        import io
        import ssl
        import zipfile

        # 构建候选版本列表
        candidate_versions = []
        if edge_full_ver and edge_full_ver not in candidate_versions:
            candidate_versions.append(edge_full_ver)

        ctx = ssl._create_unverified_context()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        # 尝试查询微软官方该大版本的最新发布版本
        if edge_major:
            try:
                rel_url = f"https://msedgedriver.microsoft.com/LATEST_RELEASE_{edge_major}_WINDOWS"
                req_rel = urllib.request.Request(rel_url, headers=headers)
                with urllib.request.urlopen(req_rel, timeout=8, context=ctx) as r:
                    raw = r.read()
                    try:
                        v_str = raw.decode("utf-16").strip()
                    except Exception:
                        v_str = raw.decode("utf-8", errors="ignore").strip()
                    if v_str and v_str not in candidate_versions:
                        candidate_versions.append(v_str)
            except Exception:
                pass

        # 兜底查询全版本 LATEST_STABLE
        if not candidate_versions:
            try:
                stable_url = "https://msedgedriver.microsoft.com/LATEST_STABLE"
                req_st = urllib.request.Request(stable_url, headers=headers)
                with urllib.request.urlopen(req_st, timeout=8, context=ctx) as r:
                    raw = r.read()
                    try:
                        v_str = raw.decode("utf-16").strip()
                    except Exception:
                        v_str = raw.decode("utf-8", errors="ignore").strip()
                    if v_str and v_str not in candidate_versions:
                        candidate_versions.append(v_str)
            except Exception:
                pass

        # 准备存储路径 (优先 AppData 目录，保证即使安装在 Program Files 等只读目录也具备写权限)
        appdata_driver = os.path.join(os.environ.get("APPDATA", ""), "NoOvertime", "driver")
        try:
            os.makedirs(appdata_driver, exist_ok=True)
        except Exception:
            pass

        # 软件本地 driver 目录 (便携版或普通用户目录)
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            local_driver = os.path.join(exe_dir, "driver")
        else:
            local_driver = os.path.abspath("driver")
        try:
            os.makedirs(local_driver, exist_ok=True)
        except Exception:
            pass

        target_name = f"msedgedriver_{edge_major}.exe" if edge_major else "msedgedriver.exe"
        appdata_target = os.path.join(appdata_driver, target_name)
        appdata_generic = os.path.join(appdata_driver, "msedgedriver.exe")

        for ver in candidate_versions:
            down_url = f"https://msedgedriver.microsoft.com/{ver}/edgedriver_win64.zip"
            try:
                self.progress(f"正在准备下载 Edge {ver} 驱动...", 0)
                req = urllib.request.Request(down_url, headers=headers)
                with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
                    if resp.status != 200:
                        continue
                    total_size = resp.getheader("Content-Length")
                    total_bytes = int(total_size) if total_size and total_size.isdigit() else 0
                    downloaded = 0
                    chunk_size = 128 * 1024
                    buffer = io.BytesIO()

                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        buffer.write(chunk)
                        downloaded += len(chunk)
                        if total_bytes > 0:
                            pct = min(99, int((downloaded / total_bytes) * 100))
                            mb_curr = downloaded / (1024 * 1024)
                            mb_total = total_bytes / (1024 * 1024)
                            self.progress(f"正在下载 Edge 驱动 ({mb_curr:.1f}MB/{mb_total:.1f}MB)...", pct)
                        else:
                            self.progress(f"正在下载 Edge 驱动...", 50)

                    self.progress("正在解压与配置 Edge 驱动...", 100)
                    buffer.seek(0)
                    z = zipfile.ZipFile(buffer)
                    extracted_bytes = None
                    for info in z.infolist():
                        if info.filename.lower().endswith("msedgedriver.exe"):
                            with z.open(info) as src:
                                extracted_bytes = src.read()
                            break

                    if not extracted_bytes:
                        continue

                    # 写入 AppData 目录
                    for path in [appdata_target, appdata_generic]:
                        try:
                            with open(path, "wb") as dst:
                                dst.write(extracted_bytes)
                        except Exception:
                            pass

                    # 尝试同步写入程序本地 driver 目录 (如果有写权限)
                    for fname in [target_name, "msedgedriver.exe"]:
                        try:
                            local_target = os.path.join(local_driver, fname)
                            with open(local_target, "wb") as dst:
                                dst.write(extracted_bytes)
                        except Exception:
                            pass

                    # 返回已成功写入且大小正常的驱动路径
                    if os.path.exists(appdata_target) and os.path.getsize(appdata_target) > 0:
                        return appdata_target
                    local_target = os.path.join(local_driver, target_name)
                    if os.path.exists(local_target) and os.path.getsize(local_target) > 0:
                        return local_target
                    if os.path.exists(appdata_generic) and os.path.getsize(appdata_generic) > 0:
                        return appdata_generic
            except Exception:
                continue

        return None
        
    def start(self, initial_url: str = "https://www.eveportal.com/login") -> webdriver.Edge:
        """启动 Edge 并通过 CDP 连接 Selenium"""
        # B3: 启动前自动打扫历史残留的过期临时 profile
        clean_stale_profiles()

        # B4: 动态探测 Edge 浏览器执行文件 (优先使用传入的自定义/配置路径)
        edge_bin = find_edge_binary(self.edge_bin)
        edge_major, edge_full_ver = get_edge_version(edge_bin)

        # 1. 驱动探测与按需自动下载：若本地无匹配驱动，先触发自动下载
        driver_path = get_driver_path(edge_bin)
        if not driver_path or not os.path.exists(driver_path):
            self.progress("检测到本地缺少 Edge 驱动，正在自动下载匹配驱动...", 0)
            driver_path = self._download_matching_driver(edge_major, edge_full_ver)
            if not driver_path or not os.path.exists(driver_path):
                raise RuntimeError(
                    f"未找到与 Microsoft Edge 匹配的 WebDriver，且自动下载未成功。\n"
                    f"当前 Edge 版本: {edge_full_ver or edge_major or '未知'}\n"
                    f"请检查网络连接或手动下载 msedgedriver.exe 放入 driver 目录。"
                )

        # 2. 检查指定端口是否已有存活的 Edge 调试实例
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
                
        # 3. 连接 Selenium
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.port}")
        
        service = Service(executable_path=driver_path)
        if sys.platform == "win32":
            service.creation_flags = subprocess.CREATE_NO_WINDOW
            
        try:
            self.driver = webdriver.Edge(service=service, options=options)
        except Exception as e:
            # 捕获驱动与 Edge 版本失配或驱动加载失败，尝试备用驱动重试或官方下载
            err_str = str(e)
            fallback_success = False
            
            # 备用候选驱动尝试 (例如 152 vs 153)
            alt_candidates = []
            if edge_major:
                alt_name = f"msedgedriver_{edge_major}.exe"
                for sdir in [os.path.dirname(driver_path) if driver_path else "", "driver"]:
                    if not sdir:
                        continue
                    p = os.path.join(sdir, alt_name)
                    if os.path.exists(p) and p != driver_path:
                        alt_candidates.append(p)
            for alt_p in alt_candidates:
                try:
                    alt_service = Service(executable_path=alt_p)
                    if sys.platform == "win32":
                        alt_service.creation_flags = subprocess.CREATE_NO_WINDOW
                    self.driver = webdriver.Edge(service=alt_service, options=options)
                    fallback_success = True
                    break
                except Exception:
                    continue

            need_download = (
                "version" in err_str.lower()
                or "session not created" in err_str.lower()
                or "unable to locate" in err_str.lower()
                or "obtain driver" in err_str.lower()
                or "driver_location" in err_str.lower()
                or "nosuchdriver" in err_str.lower()
            )

            if not fallback_success and need_download:
                new_driver = self._download_matching_driver(edge_major, edge_full_ver)
                if new_driver and os.path.exists(new_driver):
                    try:
                        auto_service = Service(executable_path=new_driver)
                        if sys.platform == "win32":
                            auto_service.creation_flags = subprocess.CREATE_NO_WINDOW
                        self.driver = webdriver.Edge(service=auto_service, options=options)
                        fallback_success = True
                    except Exception:
                        fallback_success = False

            if not fallback_success:
                if need_download:
                    edge_desc = f"（当前电脑 Edge 浏览器版本: {edge_full_ver or edge_major or '未知'}）"
                    raise RuntimeError(
                        f"Edge 浏览器版本与随包驱动不匹配 {edge_desc}！\n"
                        f"错误详情: {err_str}\n\n"
                        f"快速解决指引：\n"
                        f"1. 确认当前电脑联网正常以支持程序自动下载匹配驱动；或\n"
                        f"2. 打开 Edge 浏览器，访问 edge://settings/help 自动升级至最新版本；或\n"
                        f"3. 手动下载匹配当前 Edge 版本的 msedgedriver.exe 覆盖至软件 driver 目录。"
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

