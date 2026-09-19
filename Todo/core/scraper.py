import time
import re
from datetime import datetime, date
from typing import List, Dict, Any, Callable, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.calculator import calculate_daily_overtime

class AttendanceScraper:
    def __init__(self, driver: webdriver.Edge, progress_callback: Optional[Callable[[str, int], None]] = None):
        self.driver = driver
        self.progress = progress_callback or (lambda msg, pct: None)
        self.wait = WebDriverWait(driver, 15)
        
    def _log(self, msg: str, pct: int = 0):
        print(f"[{pct}%] {msg}")
        self.progress(msg, pct)
        
    def _wait_document_ready(self, timeout: float = 10.0) -> bool:
        """等待页面加载完成 (替代固定 sleep，早就绪早返回)"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self.driver.execute_script("return document.readyState") == "complete":
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False
        
    def _find_first_visible(self, by: str, selectors: List[str], timeout: float = 8.0):
        """
        在总超时内轮询多个候选定位表达式，返回首个可见元素，找不到返回 None。
        注意：超时是“整体”而非“每个选择器各等一次”，这是本模块提速的关键。
        """
        deadline = time.time() + timeout
        while True:
            for sel in selectors:
                try:
                    for el in self.driver.find_elements(by, sel):
                        if el.is_displayed():
                            return el
                except Exception:
                    continue
            if time.time() >= deadline:
                return None
            time.sleep(0.3)
        
    def login(self, emp_id: str, password: str) -> bool:
        """登录 EVE Portal，支持自动复用已登录会话"""
        emp_id = str(emp_id).strip()
        password = str(password).replace(" ", "")
        self._log("正在检查当前登录状态...", 5)
        
        # 优先检查是否已有标签页处于登录状态或考勤页
        for h in self.driver.window_handles:
            self.driver.switch_to.window(h)
            curr = self.driver.current_url
            if "attendance-overview" in curr or "peoplus.cn" in curr or "index" in curr:
                self._log("检测到浏览器已登录，自动复用会话！", 25)
                return True
                
        self.driver.get("https://www.eveportal.com/login")
        self._wait_document_ready(10)
        
        # 检查是否自动重定向到了首页
        if "index" in self.driver.current_url or "home" in self.driver.current_url:
            self._log("会话有效，已自动进入 Portal 首页！", 25)
            return True
            
        self._log("定位并输入工号和密码...", 10)
        # 定位工号输入框
        try:
            emp_input = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='text'].elp-input__inner, input[type='text']")
            ))
        except Exception:
            if "index" in self.driver.current_url:
                self._log("检测到已登录！", 25)
                return True
            emp_input = self._find_first_visible(By.XPATH, ["//input[@type='text']"], timeout=5)
            if not emp_input:
                raise RuntimeError("登录失败: 未能在登录页定位到工号输入框，请确认 Portal 页面是否改版")
            
        emp_input.click()
        emp_input.send_keys(Keys.CONTROL + "a")
        emp_input.send_keys(Keys.BACKSPACE)
        emp_input.send_keys(emp_id)
        
        # 定位密码输入框
        pwd_input = self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[type='password'].elp-input__inner, input[type='password']")
        ))
        pwd_input.click()
        pwd_input.send_keys(Keys.CONTROL + "a")
        pwd_input.send_keys(Keys.BACKSPACE)
        pwd_input.send_keys(password)
        
        self._log("点击【登录】按钮...", 15)
        login_btn = self.wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.elp-button--primary")
        ))
        login_btn.click()
        
        # 等待页面跳转至 index 或检测错误
        self._log("等待登录验证结果与页面加载...", 20)
        
        # 错误提示合并为单个 CSS 选择器，一次查询覆盖各类消息通知组件
        error_css = ", ".join([
            ".elp-message--error", ".elp-notification--error",
            ".el-message--error", ".elp-form-item__error",
            "div[role='alert']", ".elp-message__content"
        ])
        error_keywords = ["密码", "工号", "账号", "锁定", "失败", "错误"]
        
        logged_in = False
        deadline = time.time() + 15
        while True:
            current_url = self.driver.current_url
            if ("index" in current_url or "home" in current_url or "portal" in current_url) and "login" not in current_url:
                logged_in = True
                break
                
            for el in self.driver.find_elements(By.CSS_SELECTOR, error_css):
                try:
                    t = el.text.strip() if el.is_displayed() else ""
                except Exception:
                    continue
                if t and any(k in t for k in error_keywords):
                    raise RuntimeError(f"登录失败: {t}")
                    
            if time.time() >= deadline:
                break
            time.sleep(0.3)
            
        if not logged_in:
            # 最终检查是否有任何残留错误文本
            for sel in [".elp-message", ".elp-notification", "div[role='alert']"]:
                for el in self.driver.find_elements(By.CSS_SELECTOR, sel):
                    if el.text.strip():
                        raise RuntimeError(f"登录失败: {el.text.strip()}")
            if "login" in self.driver.current_url:
                raise RuntimeError("登录失败: 工号或密码输入错误，请重新核对！")
                
        self._log("EVE Portal 登录成功！", 25)
        return True
        
    def enter_peoplus_hr(self) -> bool:
        """从门户进入 HR 人力资源系统"""
        self._log("正在检查【HR 人力资源系统】状态...", 30)
        
        # 检查是否已有标签页直接在 peoplus
        for h in self.driver.window_handles:
            self.driver.switch_to.window(h)
            if "peoplus.cn" in self.driver.current_url:
                self._log("已找到 HR 系统标签页，直接切换！", 40)
                return True
                
        self._wait_document_ready(10)
        # 查找 HR 人力资源系统 卡片 (整体最多等 8 秒)
        hr_card = self._find_first_visible(By.XPATH, [
            "//*[contains(text(), '人力资源系统')]",
            "//div[contains(@class, 'system-item') and contains(., 'HR')]",
            "//*[text()='HR']/ancestor::div[1]"
        ], timeout=8)
        
        if not hr_card:
            self._log("未定位到卡片，直接跳转 HR 系统主页...", 35)
            self.driver.get("https://eve.peoplus.cn/homepagepro/home/index")
        else:
            current_handles = set(self.driver.window_handles)
            hr_card.click()
            time.sleep(3)
            
            new_handles = set(self.driver.window_handles) - current_handles
            if new_handles:
                self.driver.switch_to.window(list(new_handles)[0])
                
        self._log("进入 HR 人力资源系统，等待页面就绪...", 40)
        time.sleep(2)
        return True
        
    def enter_attendance_overview(self) -> bool:
        """从 HR 主页进入 考勤管理 -> 出勤概览"""
        self._log("正在定位【出勤概览】页面...", 45)
        
        # 检查当前或已有标签页是否已在出勤概览
        for h in self.driver.window_handles:
            self.driver.switch_to.window(h)
            if "attendance-overview" in self.driver.current_url:
                self._log("已处于出勤概览页面，直接执行后续操作！", 50)
                return True
                
        self._wait_document_ready(10)
        # 查找考勤管理按钮 (整体最多等 8 秒)
        att_btn = self._find_first_visible(By.XPATH, [
            "//*[contains(text(), '考勤管理')]",
            "//div[contains(@class, 'app-item') and contains(., '考勤')]"
        ], timeout=8)
        
        if not att_btn:
            self._log("直接跳转考勤出勤概览页面...", 48)
            self.driver.get("https://eve.peoplus.cn/kratos/attendance-overview/attendance-overview")
        else:
            current_handles = set(self.driver.window_handles)
            att_btn.click()
            time.sleep(3)
            
            new_handles = set(self.driver.window_handles) - current_handles
            if new_handles:
                self.driver.switch_to.window(list(new_handles)[0])
                
        time.sleep(3)
        self._log("成功进入【出勤概览】页面！", 50)
        return True


    def set_date_range(self, start_date_str: str, end_date_str: str):
        """设置考勤概览的日期范围 (如: 2026-05-01 至 2026-05-31)，并严格回读核验，防止静默抓错月份 (A2)"""
        self._log(f"设置查询日期区间: {start_date_str} 至 {end_date_str}...", 55)
        
        # 使用直接派发事件的高可靠脚本，杜绝 ElementClickInterceptedException 报错
        set_date_js = """
        const picker = document.querySelector('.right-datepicker');
        if (!picker) return 'no_picker';
        const inputs = picker.querySelectorAll('input.el-range-input');
        if (inputs.length < 2) return 'no_inputs';

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

        // 点击页面空白处收起可能弹出的日历浮层
        document.body.click();
        return 'success';
        """
        
        verify_js = """
        const picker = document.querySelector('.right-datepicker');
        if (!picker) return {ok: false, reason: 'no_picker'};
        const inputs = picker.querySelectorAll('input.el-range-input');
        if (inputs.length < 2) return {ok: false, reason: 'no_inputs'};
        return {ok: true, start: inputs[0].value.trim(), end: inputs[1].value.trim()};
        """

        success = False
        last_err = ""
        for attempt in range(1, 4):
            try:
                res = self.driver.execute_script(set_date_js, start_date_str, end_date_str)
                time.sleep(1.5)
                self.driver.execute_script("document.body.click();")
                time.sleep(0.5)

                check = self.driver.execute_script(verify_js)
                if check and check.get("ok"):
                    s_act = check.get("start", "")
                    e_act = check.get("end", "")
                    if s_act == start_date_str and e_act == end_date_str:
                        success = True
                        break
                    else:
                        last_err = f"页面当前为 [{s_act} 至 {e_act}]，与目标区间不符"
                else:
                    last_err = f"无法定位日期选择器输入框: {check.get('reason') if check else res}"
            except Exception as ex:
                last_err = str(ex)
            time.sleep(1.0)

        if not success:
            raise RuntimeError(f"设置查询月份区间失败 ({last_err})。为防止抓取错误月份，已中断执行！")
        self._log(f"已核实确认当前查询区间: {start_date_str} 至 {end_date_str}", 58)
            
    def scrape_month_records(
        self,
        year: int,
        month: int,
        calc_rules: Dict[str, Any]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        抓取当月每日打卡并进行加班工时计算
        """
        import calendar
        _, last_day = calendar.monthrange(year, month)
        start_date_str = f"{year:04d}-{month:02d}-01"
        end_date_str = f"{year:04d}-{month:02d}-{last_day:02d}"
        
        self.set_date_range(start_date_str, end_date_str)
        time.sleep(2)
        
        # 获取员工姓名 (显式轮询，最多 3 秒)
        emp_name = "员工"
        deadline = time.time() + 3
        while time.time() < deadline:
            for ne in self.driver.find_elements(
                By.CSS_SELECTOR, "[class*='user-name'], [class*='userName'], [class*='name']"
            ):
                try:
                    t = ne.text.strip()
                except Exception:
                    continue
                if t and len(t) < 10 and not any(x in t for x in ["工号", "部门", "管理", "出勤"]):
                    emp_name = t
                    break
            if emp_name != "员工":
                break
            time.sleep(0.3)
                
        self._log(f"开始抓取【{emp_name}】{year}年{month}月份每日出勤打卡...", 60)
        
        records = []
        failed_days = []
        
        # 初步先关掉可能遗留的抽屉
        try:
            self.driver.execute_script("const c = document.querySelector('.er-dialog-close'); if (c) c.click();")
            time.sleep(0.3)
        except Exception:
            pass
            
        for day in range(1, last_day + 1):
            cur_date = date(year, month, day)
            day_str = f"{day:02d}"
            target_date_str = f"{year:04d}-{month:02d}-{day_str}"
            target_slash = f"{year:04d}/{month:02d}/{day_str}"
            
            is_weekend = cur_date.weekday() >= 5
            pct = 60 + int((day / last_day) * 36)
            self._log(f"正在读取 {month:02d}月{day_str}日 打卡详情...", pct)
            
            # 1. 首先检查表格单元格状态 (是否有打卡记录、排班班次名称、加班申请标识)
            cell_info = self.driver.execute_script(f"""
                const c = document.querySelector("div[customattribute*='\\"prop\\":\\"{target_date_str}\\"']");
                if (!c) return null;
                const vacEl = c.querySelector('.date-cell-vacation');
                const isHoliday = !!vacEl;
                const classEl = c.querySelector('.date-cell-classes');
                const shift = classEl ? classEl.innerText.trim() : '白班';
                const clockEl = c.querySelector('.date-cell-clock');
                const clockItems = clockEl ? clockEl.querySelectorAll('.date-cell-clock-item') : [];
                // 检测单元格内是否有加班申请相关的标识（图标/文字）
                const cellText = c.innerText || '';
                const hasOtBadge = cellText.includes('加班') || !!c.querySelector('.date-cell-overtime, .overtime-icon, [class*="overtime"], [class*="apply"], [class*="ot"]');
                return {{
                    hasClock: clockItems.length > 0,
                    hasOtBadge: hasOtBadge,
                    cellShift: shift,
                    isStatutoryHoliday: isHoliday
                }};
            """)
            
            shift_name = cell_info.get("cellShift", "白班") if cell_info else "白班"
            is_statutory_holiday = cell_info.get("isStatutoryHoliday", False) if cell_info else False
            check_in_str = "-"
            check_out_str = "-"
            ot_valid_hours = None
            ot_check_in = None
            ot_check_out = None
            
            # 2. 打开抽屉条件：仅当在当天或过去日期，且单元格内有实际打卡记录或加班申请标识时，才打开详情抽屉
            # 未来日期或无打卡、无加班单的正常公休周末直接按排班核算，无需打开抽屉，避免无效超时与弹窗误报
            need_drawer = False
            if cell_info and cur_date <= date.today():
                if cell_info.get("hasClock") or cell_info.get("hasOtBadge"):
                    need_drawer = True

            drawer_success = True
            if need_drawer:
                drawer_success = False
                try:
                    # 滚动并点击日期单元格中的打卡项或加班标识
                    self.driver.execute_script(f"""
                        const c = document.querySelector("div[customattribute*='\\"prop\\":\\"{target_date_str}\\"']");
                        if (c) {{
                            c.scrollIntoView({{block: 'center', inline: 'center'}});
                            const target = c.querySelector('.date-cell-clock-item, .date-cell-overtime, .overtime-icon, [class*="overtime"]') || c.querySelector('.date-cell-clock-item') || c;
                            target.click();
                        }}
                    """)
                    
                    # 严密等待抽屉加载遮罩消失且日期完全同步对齐
                    t0 = time.time()
                    while time.time() - t0 < 6.0:
                        res = self.driver.execute_script("""
                            const warp = document.querySelector('.er-dialog-warp');
                            if (!warp) return {ready: false};
                            const mask = warp.querySelector('.el-loading-mask');
                            if (mask && mask.style.display !== 'none') return {ready: false};
                            
                            let foundDate = '';
                            const labels = warp.querySelectorAll('.item-container');
                            for (let item of labels) {
                                const lbl = item.querySelector('.item-label');
                                const val = item.querySelector('.item-value');
                                if (lbl && lbl.innerText.includes('考勤日期') && val) {
                                    foundDate = val.innerText.trim();
                                }
                            }
                            const titleEl = warp.querySelector('.attendance-day-end-audit-title .title-left');
                            const title = titleEl ? titleEl.innerText : '';
                            
                            let shift = '';
                            for (let item of labels) {
                                const lbl = item.querySelector('.item-label');
                                const val = item.querySelector('.item-value');
                                if (lbl && lbl.innerText.includes('考勤班次') && val) {
                                    shift = val.innerText.trim();
                                }
                            }
                            
                            // 打卡时间严格从考勤时间轴获取，避免被下方的加班申请单数据混淆
                            let checkIn = '-';
                            let checkOut = '-';
                            const attInfo = warp.querySelector('.attendance-info');
                            if (attInfo) {
                                const blocks = attInfo.querySelectorAll('.timeline-content-block-div');
                                for (let b of blocks) {
                                    const fl = b.querySelector('.field-label');
                                    const fv = b.querySelector('.field-value');
                                    if (fl && fv) {
                                        const txt = fl.innerText.trim();
                                        const v = fv.innerText.trim();
                                        if (txt === '上班打卡时间') checkIn = v;
                                        if (txt === '下班打卡时间') checkOut = v;
                                    }
                                }
                            }
                            
                            // 加班信息 (周末或节假日加班申请单)
                            let otValidHours = null;
                            let otIn = null;
                            let otOut = null;
                            const otSection = warp.querySelector('.work-overtime-info');
                            if (otSection) {
                                const rows = otSection.querySelectorAll('.info-row');
                                for (let r of rows) {
                                    const rowLabels = r.querySelectorAll('.item-label');
                                    const rowVals = r.querySelectorAll('.item-value');
                                    for (let i = 0; i < rowLabels.length; i++) {
                                        const lbl = rowLabels[i].innerText.trim();
                                        const val = rowVals[i] ? rowVals[i].innerText.trim() : '';
                                        if (lbl === '有效加班时长' || lbl === '实际加班时长') {
                                            const m = val.match(/([0-9.]+)/);
                                            if (m && otValidHours === null) {
                                                otValidHours = parseFloat(m[1]);
                                            }
                                        }
                                        if (lbl === '上班打卡时间' && val && val !== '-') {
                                            otIn = val;
                                        }
                                        if (lbl === '下班打卡时间' && val && val !== '-') {
                                            otOut = val;
                                        }
                                    }
                                }
                            }
                            
                            return {
                                ready: true,
                                foundDate: foundDate,
                                title: title,
                                shift: shift,
                                checkIn: checkIn,
                                checkOut: checkOut,
                                otValidHours: otValidHours,
                                otIn: otIn,
                                otOut: otOut
                            };
                        """)
                        if res and res.get('ready') and (target_slash in res.get('foundDate', '') or target_slash in res.get('title', '')):
                            if res.get('shift'):
                                shift_name = res['shift']
                            check_in_str = res.get('checkIn', '-')
                            check_out_str = res.get('checkOut', '-')
                            ot_valid_hours = res.get('otValidHours')
                            ot_check_in = res.get('otIn')
                            ot_check_out = res.get('otOut')
                            drawer_success = True
                            break
                        time.sleep(0.1)
                        
                    if not drawer_success:
                        failed_days.append(target_date_str)
                        self._log(f"⚠️ {target_date_str} 详情抽屉加载超时，打卡可能未完全同步", pct)

                    # 点击日历格读取数据后，停留两秒再关闭抽屉并进入下一天
                    time.sleep(2.0)

                    # 采集完当前日期后立即关闭抽屉，保持界面干净且不遮挡后续单元格
                    self.driver.execute_script("const c = document.querySelector('.er-dialog-close'); if (c) c.click();")
                    time.sleep(0.3)
                except Exception as ex:
                    failed_days.append(target_date_str)
                    print(f"读取 {target_date_str} 详情异常: {ex}")
                    try:
                        self.driver.execute_script("const c = document.querySelector('.er-dialog-close'); if (c) c.click();")
                    except Exception:
                        pass
                        
            # 如果常规时间段无打卡，但加班申请单中有打卡时间，采用加班单的打卡时间
            if (check_in_str == '-' or not check_in_str) and ot_check_in:
                check_in_str = ot_check_in
            if (check_out_str == '-' or not check_out_str) and ot_check_out:
                check_out_str = ot_check_out
                
            # 规则计算
            item_result = calculate_daily_overtime(
                record_date=cur_date,
                shift_name=shift_name,
                check_in_str=check_in_str,
                check_out_str=check_out_str,
                weekday_standard_end=calc_rules.get("weekday_end", "17:30"),
                weekday_ot_start=calc_rules.get("weekday_ot_start", "18:00"),
                min_ot_minutes=calc_rules.get("min_ot_minutes", 30),
                granularity_minutes=calc_rules.get("granularity_minutes", 30),
                ot_valid_hours=ot_valid_hours,
                is_statutory_holiday=is_statutory_holiday,
                ot_latest_end=calc_rules.get("ot_latest_end", "02:00"),
                include_weekend_base=calc_rules.get("include_weekend_base", True)
            )
            if target_date_str in failed_days:
                orig_note = item_result.get("notes", "")
                prefix = "⚠️【抽屉读取超时，打卡数据可能有遗漏】"
                item_result["notes"] = f"{prefix} {orig_note}" if orig_note else prefix

            records.append(item_result)
            
        # 采集完成后关闭抽屉
        try:
            self.driver.execute_script("""
                const btn = document.querySelector('.er-dialog-close');
                if (btn) btn.click();
            """)
        except Exception:
            pass
            
        if failed_days:
            self._log(f"采集完成！其中 {len(failed_days)} 天存在读取超时异常", 98)
        else:
            self._log("当月所有日期打卡数据采集并核算完成！", 98)
        return emp_name, records, failed_days

