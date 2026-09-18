# NoOvertime 代码审查与优化清单

- **审查范围**：`main.py`、`core/`、`gui/`、`utils/`、`tests/`、`NoOvertime.spec`、`installer.iss`（约 3.6k 行）
- **技术栈**：Python 3.13 + PyQt5 + Selenium(Edge CDP) + openpyxl + Pillow，PyInstaller 6.16 打包
- **文档说明**：汇总全部审查发现，共 **60 个条目**（14 项已修复 + 46 项待处理）。第 1 节为已修复项，第 2 节为待处理项（按优先级），第 3 节明确尚未验证的边界，附录 D 给出**逐文件的审查覆盖清单**。

---

## 0. 结论速览

| 分类 | 数量 | 状态 |
| --- | --- | --- |
| 已修复（本轮） | 14 项（F1–F14） | ✅ 已验证（25 项单测 + 离屏/真实渲染 + EXE 冒烟） |
| P0 会导致数据算错 | 4 项（A1–A4） | ⏳ 待处理（其中 1 项需业务口径拍板） |
| P1 会误伤环境 / 静默失效 | 8 项（B1–B8） | ⏳ 待处理 |
| P2 功能与体验 | 14 项（C1–C14） | ⏳ 待处理 |
| P3 架构与工程卫生 | 8 项（D1–D8） | ⏳ 待处理 |
| P3 安装包与启动脚本 | 5 项（E1–E5） | ⏳ 待处理 |
| P4 次要观察 | 7 项（G1–G7） | 📝 记录在案，无需急办 |

> 字母 F 已用于「已修复项」，故待处理项跳过 F，直接由 E 接 G。

**最需要优先处理的三条**（会让报表数字直接出错）：`A1 周末口径矛盾`、`A2 日期区间静默失败`、`A3 单日静默漏读`。

---

## 1. 已修复项（本轮会话）

| # | 问题 | 修复方式 | 涉及文件 |
| --- | --- | --- | --- |
| F1 | 表格「加班计算依据与备注」列永远为空 | 键名 `remark` → `notes`（calculator 产出的是 `notes`，Excel 导出一直是对的，只有界面读错） | `gui/main_window.py` |
| F2 | 跨天下班算错/漏算 | 新增 `normalize_check_out()`：下班 ≤ 上班、或落在 08:30 前的凌晨，自动对齐次日 | `core/calculator.py` |
| F3 | 加班无上限、18:00 起算点锚定错误 | 新增 `resolve_ot_window()`：**18:00 起算 → 次日 02:00 截止**，两端都锚定考勤日；超出部分写入备注 | `core/calculator.py` |
| F4 | 周末部分出勤虚高 1 小时 | 新增 `standard_work_hours()`：按 08:30-12:00 / 13:00-17:30 求重叠，午休天然排除 | `core/calculator.py` |
| F5 | `granularity_minutes=0` 触发 ZeroDivisionError | `step = max(1, int(granularity_minutes or 0))` | `core/calculator.py` |
| F6 | 闰日 `02-29` 解析失败、跨年打卡错位一年 | `parse_time_str` 改为补齐年份后解析 + 跨年 ±300 天修正 | `core/calculator.py` |
| F7 | **每次统计白等 1~2 分钟** | `implicitly_wait(10)` → `0`；新增 `_wait_document_ready()`、`_find_first_visible()`（整体超时而非逐选择器叠加）；登录错误提示合并为单次 CSS 查询 | `core/edge_cdp.py`、`core/scraper.py` |
| F8 | 开机自启（cwd=System32）读不到配置、托盘图标丢失 | 新增 `utils/paths.py`：`resource_path()` 基于 `_MEIPASS`/EXE 目录解析；配置迁至 `%APPDATA%\NoOvertime\config.json`，含旧位置一次性迁移 + 原子写 | `utils/paths.py`、`utils/config_mgr.py`、`main.py`、`gui/*` |
| F9 | 密码明文存 `config.json` | 新增 `utils/crypto.py`（Windows DPAPI，纯 ctypes 无新依赖）；字段改 `saved_password_enc`，加载时自动加密旧明文并**从磁盘清除** | `utils/crypto.py`、`utils/config_mgr.py` |
| F10 | 背景图每次改设置都重新解码+高斯模糊；paintEvent 每帧缩放 | `load_and_process_bg` 按 (路径, mtime, 模糊半径) 缓存；`BackgroundCentralWidget` 缓存缩放结果，`resizeEvent` 才失效 | `gui/main_window.py` |
| F11 | 生产界面常驻「加载演示数据」 | 默认隐藏，由 `debug_mode` 配置或 `--debug` 参数控制；设置页新增「调试与诊断」开关 | `gui/main_window.py`、`gui/settings_dialog.py` |
| F12 | 设置页 tab 蓝色高亮、右侧多余空白块、页面内容重叠看不清 | tab 改中性下划线（去蓝）、高度 47→34px、去掉 `setExpanding`；每页套 `QScrollArea`；「启动设置」页压紧后 500px 高度内完整显示 | `gui/settings_dialog.py` |
| F13 | 「开机自启」与「静默进托盘」耦合成一个选项 | 拆成两个独立开关；注册表命令按需拼 `--tray`；新增托盘气泡提示；旧配置自动迁移保留原行为 | `gui/settings_dialog.py`、`utils/autostart_mgr.py`、`main.py` |
| F14 | 其他 | scraper 移除硬编码个人姓名 XPath；`autostart_mgr` 路径改基于工程根；`installer.iss` 移除已失效的 config.json 分发规则；新增 `tests/test_calculator.py`（25 项） | 多处 |

---

## 2. 待处理项

### P0 · 会导致报表数字算错

#### A1 周末加班口径自相矛盾 ⚠️ 需业务拍板

- **现象**：有审批单且核定 0h → 计 **0h**；**没有**审批单（`ot_valid_hours is None`）→ 走打卡兜底，凭出勤直接给 **8h**。同一天有没有那张单子，结果差 8 小时。
- **位置**：<ref_snippet file="E:/HR客户端/App/Harness/Todo/core/calculator.py" lines="262-280" />（`calculate_daily_overtime` 规则 5 分支，`base_weekend_hours` 计算处 line 269）
- **影响**：直接影响月合计与津贴档位。合计 71h 已在等级 11（1100 元）边缘，一天误差就可能跳档。
- **建议**：三种口径任选其一——(a) 一律以审批单为准，无单计 0；(b) 保留兜底但在备注标注「未经审批、仅供参考」且 KPI 分开统计；(c) 做成「核算规则」设置页里的可配置项（顺带把 A5 的两个死配置接上）。

#### A2 日期区间设置失败不中断，会抓错月份

- **现象**：`set_date_range` 的 JS 返回 `'no_picker'` / `'no_inputs'` 时，返回值 `res` **完全没被检查**，只在抛异常时打印一句日志，随后照常往下抓。
- **位置**：<ref_snippet file="E:/HR客户端/App/Harness/Todo/core/scraper.py" lines="250-258" />
- **影响**：抓到的是页面上**当前显示的月份**，用户得到一份月份错误、但界面与 Excel 都看起来完全正常的报表。属最危险的静默错误。
- **建议**：检查返回值；设置后回读两个 `input.el-range-input` 的 value 与目标区间比对，不一致直接 `raise`，让统计明确失败而不是给出错数据。

#### A3 单日抽屉读取超时被静默吞掉

- **现象**：抽屉 6 秒内没等到日期对齐时，`except` 里只 `print` 一句，该日 `check_in/check_out` 保持 `-`、加班算 0。
- **位置**：<ref_snippet file="E:/HR客户端/App/Harness/Todo/core/scraper.py" lines="371-374" />（等待循环）、line 474（异常打印）
- **影响**：31 天里漏读 3 天，界面和导出都看不出异常，合计直接少算。
- **建议**：收集失败日期列表，随 `finished_signal` 回传；结束时在状态栏/弹窗明确提示「有 N 天未读取成功」，并在 Excel 对应行标注。

#### A4 津贴阶梯在 90 小时整点上实现与注释矛盾

- **现象**：`elif h <= 90: return 1400`，但同一函数注释写「等级 15：H ≥ 90 → 1500」。90.0 到底算哪档，代码与文档冲突。
- **位置**：<ref_snippet file="E:/HR客户端/App/Harness/Todo/core/calculator.py" lines="330-336" />
- **建议**：确认公司口径后统一（大概率应为 `h < 90` → 1400），并补边界单测。

---

### P1 · 会误伤运行环境 / 静默失效

#### B1 可能关闭用户自己的浏览器

- **现象**：`quit()` 在「端口已存活（复用现有浏览器）」的分支里 `self.proc` 为 `None`，但仍然执行 `driver.quit()`。
- **位置**：<ref_snippet file="E:/HR客户端/App/Harness/Todo/core/edge_cdp.py" lines="125-135" />
- **影响**：若 9222 上是用户自己开的调试 Edge，统计结束会把它一起关掉。
- **建议**：记录「浏览器是否由本程序启动」，非自启动的会话只 `driver.close()` 当前标签或直接释放 driver，不 quit 浏览器。

#### B2 调试端口固定 9222，可能挂到无关实例

- **现象**：`_is_port_alive()` 为真就直接 attach。
- **位置**：`core/edge_cdp.py`（`__init__` 默认 `port=9222`、`start()` 开头）
- **建议**：默认取随机空闲端口；仅在用户显式要求复用时才连固定端口。

#### B3 临时 profile 目录会无限堆积

- **现象**：`tempfile.mkdtemp(prefix="edge_hr_profile_")` 只在正常 `quit()` 时清理，进程被 `terminate()` 或崩溃时残留。
- **位置**：`core/edge_cdp.py`（`start()` / `quit()`）
- **影响**：`%TEMP%\edge_hr_profile_*` 每个几十 MB，长期占满磁盘。
- **建议**：启动时扫描并清扫超过 1 天的同前缀目录。

#### B4 Edge 可执行路径只认 32 位安装目录

- **现象**：`DEFAULT_EDGE_BIN = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"` 硬编码。
- **位置**：`core/edge_cdp.py` line 14
- **建议**：多路径回退 + 读注册表 `App Paths\msedge.exe`；找不到时给明确的中文错误提示。

#### B5 随包 msedgedriver 与 Edge 自动升级版本失配

- **现象**：driver 固定随包，Edge 静默升级后握手失败。
- **建议**：失败时回退 Selenium Manager 自动匹配；并把「driver 版本不匹配」翻译成用户能懂的提示。

#### B6 自启注册表不校验路径

- **现象**：`is_autostart_enabled()` 只判断键是否存在。
- **位置**：<ref_snippet file="E:/HR客户端/App/Harness/Todo/utils/autostart_mgr.py" lines="12-18" />
- **影响**：程序换目录/重装后注册表仍指向旧 exe，自启实际失效，而设置界面照样显示「已勾选」。
- **建议**：读值比对当前 exe 路径，不一致则自动改写。

#### B7 没有单实例保护

- **现象**：无 `QSharedMemory`/`QLocalServer` 检查。
- **影响**：**已实测踩坑**——自启 + 手动启动导致两个实例并存，两个托盘图标、两个 Edge、抢同一个 9222 端口，并锁住 `dist` 目录使打包失败。
- **建议**：`QSharedMemory` 加锁，第二个实例直接激活已有窗口后退出。

#### B8 无日志、无全局异常兜底、无托盘可用性检查

- **现象**：全项目仅 `print`（`console=False` 的 windowed EXE 里 stdout 是黑洞）；没有 `sys.excepthook`；`main.py` 未检查 `QSystemTrayIcon.isSystemTrayAvailable()`。
- **位置**：`main.py` line 37 附近（静默启动判断）
- **影响**：出问题拿不到任何线索；托盘服务异常 + 「启动后隐藏到托盘」= 既无窗口又无图标的幽灵进程。
- **建议**：`logging` + `RotatingFileHandler` 写 `%APPDATA%\NoOvertime\logs`；`sys.excepthook` 记录并弹窗；托盘不可用时强制显示主窗口。

---

### P2 · 功能与体验

#### C1 「记住工号/密码」可能白勾

- **现象**：`save_current_config()` 全项目**只有一个调用点**——点【开始统计】时。
- **位置**：`gui/main_window.py` line 1022（定义）、line 1048（唯一调用）
- **影响**：勾选后直接关窗口，工号/密码不会落盘。
- **建议**：勾选状态变化时立即保存，并在 `closeEvent` 兜底。

#### C2 定时防息屏被静默重置且不持久化

- **现象**：`apply_new_settings` 只要 `awake_enabled` 为真就调 `enable()`，而 `enable()` 每次重算 `end_time`。程序启动时 `load_saved_config()`（line 1017）与 `apply_new_settings()`（line 883）会连调两次。
- **影响**：每次打开设置点【确定】，「还剩 20 分钟」被重置为整整 2 小时；重启后倒计时从头开始。
- **建议**：`enable()` 增加「若已激活且模式/时长未变则不重置」判断；把 `end_time` 持久化到配置。

#### C3 深色主题下所有弹窗仍是白底

- **现象**：`StyledMessageBox` 样式表把 `#FFFFFF`/`#334155` 写死。
- **位置**：<ref_snippet file="E:/HR客户端/App/Harness/Todo/gui/styled_dialog.py" lines="34-70" />
- **附带**：定义了 `btn_dialog_cancel` 样式但从未使用；`sys`、`QIcon`、`QColor`、`QFrame` 是死导入。
- **建议**：接受 `is_dark` 参数或从父窗口读主题，与主界面配色统一。

#### C4 Excel 报表副标题的核算区间缺结束日

- **现象**：`f"{year}年{month:02d}月01日 至 {year}年{month:02d}月"` → 导出成「2026年08月01日 至 2026年08月」。
- **位置**：`gui/main_window.py` line 1227
- **建议**：补 `calendar.monthrange` 得到的月末日。

#### C5 密码被 `.strip()`

- **现象**：登录用 `text().strip()`，保存用原值。
- **位置**：`gui/main_window.py` line 1035
- **影响**：密码首尾含空格时出现「有时能登、有时登不上」的玄学现象。
- **建议**：工号可 strip，密码原样使用。

#### C6 「法定节假日(不计)」KPI 卡永远显示 0.0

- **现象**：节假日分支强制 `overtime_hours = 0`，KPI 又只累加该字段。
- **位置**：`gui/main_window.py` line 1142
- **建议**：记录 `declared_ot_hours`（申报时长）并用于该卡片展示，才有信息量。

#### C7 表格数字列按字符串排序，且未开启排序

- **现象**：单元格存的是 `"3.5 小时"` 字符串；全项目无 `setSortingEnabled`。
- **位置**：`gui/main_window.py` line 1150
- **建议**：`setData(Qt.EditRole, float)` + 开启排序，让「按加班时长排序」可用。

#### C8 进度文本被统一覆盖，丢失诊断信息

- **现象**：`on_worker_progress` 把 scraper 精心写的「正在读取 09月12日 打卡详情…」替换成 `Loading... [x%]`。
- **位置**：`gui/main_window.py` line 1069-1077
- **建议**：进度条显示百分比，状态栏保留原始文案。

#### C9 无「取消统计」按钮，退出时强杀线程

- **现象**：`quit_app` 用 `worker_thread.terminate()`。
- **建议**：加协作式取消标志（scraper 每日循环检查），提供「取消」按钮；避免 `terminate()` 造成 Selenium/COM 资源泄漏。

#### C10 `ScraperThread` 的 `headless` 是死参数

- **现象**：构造函数接收，`run()` 里硬写 `headless=True`。
- **建议**：接上参数或删掉，避免调试时误以为能可视化。

#### C11 两个死配置项 + 缺「核算规则」设置页

- **现象**：`exclude_public_holiday`、`include_weekend_base` 代码从未读取。
- **位置**：`utils/config_mgr.py` line 17-18
- **附带**：设置面板只有个性化/Awake/启动设置三页，所有核算阈值（18:00、30 分钟、颗粒度、02:00 上限）用户都改不了。
- **建议**：新增「核算规则」页，把这些项真正接上（与 A1 一并做）。

#### C12 演示数据硬编码个人信息

- **现象**：`load_mock_data` 里写死「刘习俊」与 5 月节假日。
- **位置**：`gui/main_window.py` line 1239-1283
- **建议**：改为通用示例数据。

#### C13 日历视图每次全量重建

- **现象**：`update_calendar` 每次 `takeAt` + `deleteLater` 重建 35+ 个 `DayCellWidget`，切月份、切主题都触发。
- **位置**：`gui/calendar_view.py` line 223-279
- **建议**：复用单元格，只更新数据与配色；顺带补上「点击某天看备注」的交互（当前日历不可点）。

#### C14 无采集结果缓存

- **现象**：每次查询都完整跑一遍浏览器流程。
- **建议**：按 `emp_id + 年月` 缓存 JSON，重复查询/离线重新导出 Excel 秒开。

---

### P3 · 架构与工程卫生

#### D1 改抓 XHR 接口（收益最大）

- **现象**：逐日点抽屉 31 次，且强依赖 `.er-dialog-warp`、`.date-cell-clock-item`、`customattribute*='"prop":"..."'` 等 DOM class。
- **影响**：耗时分钟级；HR 系统一改版整套采集失效。
- **建议**：用浏览器 Cookie 转 `requests`（或 CDP `Network` 域）直接请求考勤接口，一次拿整月 → 秒级且稳定。需先跑一次真实登录抓取接口结构。

#### D2 「复用已登录会话」是死代码

- **现象**：`start()` 每次 `tempfile.mkdtemp()` 建全新 profile，Cookie 必为空，`login()` 开头的会话复用检测永远命中不了。
- **位置**：`core/edge_cdp.py`（临时目录）＋ `core/scraper.py`（`login` 开头）
- **建议**：改用固定 profile 目录，可省掉整个登录环节甚至免密。

#### D3 URL 与选择器散落各处

- **现象**：3 个硬编码 URL、十余个 CSS/XPath 分散在方法内。
- **建议**：集中到常量模块或外部配置，改版时只改一处。

#### D4 打包体积约 30MB 是死重量

- **现象**：`dist\NoOvertime` 共 195MB，其中 `numpy 7MB + numpy.libs 21MB`（项目零处 import numpy，由 PIL 的 hook 顺带拉入），另有 `psutil`/`yaml`/`win32` 各 1MB。spec 里 `excludes=[]`。
- **建议**：`excludes=['numpy','pandas','pygame','matplotlib','tkinter','psutil','yaml']` 后验证启动，可砍约 30MB。

#### D5 `upx=True` 是隐患

- **现象**：本机未装 UPX 时静默跳过（等于没压缩）；真启用是国内杀软误报高发点。
- **建议**：显式改 `upx=False`。

#### D6 `requirements.txt` 与实际依赖不符

- **现象**：缺 **Pillow**（`gui/main_window.py` 直接 `from PIL import ...`，靠 spec 的 hiddenimports 兜着），多余 **pandas**（全项目零引用）；版本全是 `>=` 未锁定。
- **建议**：补 Pillow、删 pandas、锁定版本。

#### D7 工程卫生

- **现象**：仍**没有 git 仓库**，无 `.gitignore`；根目录混着 16 个 `test_*/inspect_*` 探针脚本、3 个 `.spec`、6 个 `.bat/.vbs` 启动器；`dist/` 下历史产物约 613MB（`EVE考勤与加班统计` 240M、`不加了` 240M + `不加了.rar` 79M、`x64` 54M），`build/` 另占 66M。
- **建议**：`git init` 立基线 → 探针脚本归入 `tools/` → 只保留 `NoOvertime.spec` → 清理历史产物（需确认后执行）。

#### D8 测试覆盖仅限 calculator

- **现象**：`tests/test_calculator.py` 25 项（跨天、02:00 封顶、起算线/颗粒度、午休、节假日/公休/加班单优先级、跨年闰日、除零）全绿；`config_mgr`/`crypto`/`paths` 只做过手工验证，未沉淀为测试。
- **建议**：补 `config_mgr` 迁移测试（旧明文→DPAPI、旧路径→%APPDATA%）与 `paths` 的 frozen/非 frozen 解析测试。

---

### P3 · 安装包与启动脚本

#### E1 六个启动脚本里有四个是坏的 ⚠️ ✅ **已处理：全部归档至 `script/launchers/` 并改写路径**

| 脚本 | 指向 | 状态 |
| --- | --- | --- |
| `启动EXE.bat` | `dist\EVE_App\EVE_App.exe` | ❌ **该目录根本不存在**，双击必然失败 |
| `启动程序.bat` | `dist\EVE考勤与加班统计\...exe` | ⚠️ 指向**旧项目** |
| `运行EXE.bat` → `启动EXE程序.vbs` | `dist\不加了\不加了.exe` | ⚠️ 指向**旧项目** |
| `启动不加了.vbs` | `dist\不加了\不加了.exe` | ⚠️ 与 `启动EXE程序.vbs` **内容完全相同**（重复文件） |
| `启动软件.bat` | `python main.py` | ✅ 源码启动可用 |
| `启动NoOvertime.vbs` | `dist\NoOvertime\NoOvertime.exe` | ✅ 当前项目 |

- **影响**：用户/同事双击到前四个，会启动旧版本程序（拿到用旧规则算的报表）或直接报错，且很难意识到自己启动错了。
- **建议**：只保留 `启动软件.bat`（开发）与 `启动NoOvertime.vbs`（正式），其余删除。

#### E2 卸载不清理用户数据目录

- **现象**：`installer.iss` 无 `[UninstallDelete]` 段。
- **影响**：卸载后 `%APPDATA%\NoOvertime\`（含配置与 DPAPI 密码密文）残留。
- **建议**：明确策略——要么加 `[UninstallDelete] Type: filesandordirs; Name: "{userappdata}\NoOvertime"`，要么在卸载向导里询问「是否保留设置」。至少不应默认静默残留凭据。

#### E3 EXE 没有版本资源

- **现象**：`installer.iss` 里 `MyAppVersion "2.0.0"`，但 `NoOvertime.spec` 的 `EXE()` 没有 `version=` 参数。
- **影响**：右键 EXE 属性看不到版本号/公司名；杀软与企业 IT 审计对无版本信息的未签名 EXE 更敏感；也无法从文件本身判断用户在跑哪个版本（排障困难）。
- **建议**：生成 `version_info.txt` 并在 spec 里引用，与 iss 的版本号统一维护。

#### E4 安装包未签名

- **现象**：无 SignTool 配置。
- **影响**：首次运行会触发 SmartScreen「未知发布者」警告。
- **建议**：内部分发可接受；若要给同事用，考虑自签名证书 + 内网信任，或至少在使用说明里提示。

#### E5 安装包输出目录与构建产物混在一起

- **现象**：`OutputDir=dist\x64`（当前 54MB 旧安装包），与 PyInstaller 的 `dist\NoOvertime` 同级。
- **建议**：改到 `release/` 之类的独立目录，避免与构建产物互相干扰、也便于清理。

---

### P4 · 次要观察（已知，影响很小）

| # | 现象 | 位置 | 影响 |
| --- | --- | --- | --- |
| G1 | 定时防息屏每秒 `_emit_state()` → 主窗口按钮 `unpolish/polish` 重绘一次 | `core/awake_mgr.py` `_on_tick`、`gui/main_window.py` `on_awake_state_changed` | 每秒一次小重绘，可只在文案变化时刷新 |
| G2 | 配置文件无并发写保护，两个实例同时运行时后写覆盖先写 | `utils/config_mgr.py` `save_config` | 已由 B7 单实例从根上规避 |
| G3 | 顶部核算规则说明标签未开 `setWordWrap`，窄窗口会被截断 | `gui/main_window.py` `rule_tip` | 文案本轮变长了，1000px 最小宽度下尚可 |
| G4 | 每次应用设置都重建整串 QSS 并 `setStyleSheet` 到主窗口 | `gui/main_window.py` `apply_new_settings` | 触发全窗 re-polish，仅在点【确定】时发生 |
| G5 | Excel 无冻结窗格 / 自动筛选；合计行用 `=SUM()` 公式而备注用 Python 计算值 | `utils/exporter.py` | 手工编辑单元格后两处可能不一致 |
| G6 | 密码「显示」后不会自动回隐 | `gui/main_window.py` `toggle_password_echo` | 肩窥风险，建议加超时自动隐藏 |
| G7 | 表格不支持右键复制/导出选中区域 | `gui/main_window.py` 表格初始化 | 想摘几行发消息时只能手抄 |

---

## 3. 尚未验证的边界（诚实说明）

| 项 | 说明 |
| --- | --- |
| 真实登录端到端 | **未跑过**连接真实 HR 系统的完整流程。隐式等待移除后的实际耗时、以及新的显式等待（8s/3s 上限）在真实页面上是否足够，目前只是推理。需要跑一次统计看日志确认。 |
| 高 DPI 缩放 | 未在 125% / 150% 缩放下验证。代码里大量 `setFixedWidth/setFixedHeight`（如 56px 的迷你按钮、75px 年份框），缩放后中文可能被截断。 |
| HR 页面改版兼容性 | 未做过选择器容错测试，无法判断改版后的失败模式是否可读。 |
| 重绘性能 | 表格 31 行 + 主题切换 + 日历重建的开销只做了代码层面判断，未做实测 profiling。 |
| Excel 兼容性 | 导出文件未在 WPS / 旧版 Excel 中打开验证（合计行用的是 `=SUM()` 公式）。 |

---

## 4. 建议实施路线

| 阶段 | 内容 | 理由 |
| --- | --- | --- |
| 第 0 步 | `git init` + `.gitignore` | 后续改造才有回退余地（D7） |
| 第 1 步（快赢） | B7 单实例、B8 日志+异常兜底+托盘检查、C1 记住工号落盘、C4/C5 两个小 bug、C2 防息屏重置、C3 深色弹窗、D4/D5 打包瘦身、**E1 删掉四个坏启动脚本** | 改动小、零风险；B7/B8 解决已实测痛点，E1 防止误启动旧版本 |
| 第 2 步（堵数据口子） | A2 日期区间校验、A3 失败日期上报、A4 边界统一 | 防止"看起来正常其实算错"的报表 |
| 第 3 步（需拍板） | A1 周末口径 + C11 核算规则设置页 | 需先确认公司实际核发口径 |
| 第 4 步（大改造） | D1 XHR 接口采集 + D2 固定 profile + C14 缓存 | 一次性解决慢与脆，需先抓真实接口 |
| 第 5 步（体验与分发） | C6~C10、C12、C13、E2 卸载清理、E3 版本资源、E5 输出目录 | 打磨 |
| 随手 | P4（G1–G7） | 顺路遇到就改，不单独排期 |

---

## 5. 附录

### 附录 A · 打包产物体积构成（`dist/NoOvertime`，共 195MB）

| 目录 | 体积 | 是否必需 |
| --- | --- | --- |
| `_internal/PyQt5` | 76MB | ✅ 必需 |
| `_internal/driver`（msedgedriver） | 33MB | ✅ 必需 |
| `_internal/numpy.libs` | 21MB | ❌ 未使用 |
| `_internal/selenium` | 18MB | ✅ 必需 |
| `_internal/PIL` | 11MB | ✅ 必需（背景模糊） |
| `_internal/numpy` | 7MB | ❌ 未使用 |
| `_internal/lxml` | 7MB | ⚠️ openpyxl 可选加速，可评估 |
| `python313.dll` / `libcrypto-3.dll` | 11MB | ✅ 必需 |
| `psutil` / `yaml` / `win32` | 各 1MB | ❌ 未使用 |

### 附录 B · 配置项生效情况（`%APPDATA%\NoOvertime\config.json`，共 24 项）

| 配置项 | 是否生效 | 备注 |
| --- | --- | --- |
| `emp_id` / `remember_emp_id` | ⚠️ | 仅在点【开始统计】时落盘（C1） |
| `saved_password_enc` / `remember_password` | ✅ | DPAPI 加密（F9） |
| `weekday_end` | ✅ | 本轮接上（周末下午班次末端） |
| `weekday_ot_start` | ✅ | 加班起算时刻 |
| `ot_latest_end` | ✅ | 本轮新增，默认 `02:00` |
| `min_ot_minutes` / `granularity_minutes` | ✅ | 起算线与颗粒度 |
| `exclude_public_holiday` | ❌ | **代码从未读取**（C11） |
| `include_weekend_base` | ❌ | **代码从未读取**（C11） |
| `theme` / `window_opacity` / `bg_image_path` / `mask_density` / `blur_radius` | ✅ | 外观 |
| `close_action` | ✅ | 关窗行为 |
| `custom_export_path` | ✅ | 默认导出目录 |
| `awake_enabled` / `awake_mode` / `awake_hours` | ⚠️ | 生效，但定时模式会被重置且不持久化（C2） |
| `autostart` | ✅ | 写 HKCU Run，但不校验路径（B6） |
| `start_minimized` | ✅ | 本轮新增，与自启解耦（F13） |
| `debug_mode` | ✅ | 本轮新增，控制演示数据按钮（F11） |

### 附录 C · 当前测试现状

```
tests/test_calculator.py ... 25 passed
  TestWeekdayOvertime      起算线 / 颗粒度向下取整
  TestCrossDayOvertime     跨天对齐 / 次日 02:00 封顶 / 自定义截止 / 备注文案
  TestStandardWorkHours    午休排除 / 班次外不计
  TestWeekendAndHoliday    审批单优先 / 公休 / 法定节假日 / 周末跨天
  TestTimeParsing          闰日 / 跨年
  TestRobustness           颗粒度为 0 / 非法时间配置
  TestAllowance            津贴阶梯
```

运行方式：`python -m pytest tests -q`

### 附录 D · 审查覆盖清单（逐文件）

| 文件 | 覆盖程度 |
| --- | --- |
| `main.py` | ✅ 通读 |
| `core/calculator.py` | ✅ 通读（并重写） |
| `core/scraper.py` | ✅ 通读 |
| `core/edge_cdp.py` | ✅ 通读 |
| `core/awake_mgr.py` | ✅ 通读 |
| `gui/main_window.py` | ✅ 通读（1264 行） |
| `gui/settings_dialog.py` | ✅ 通读 |
| `gui/calendar_view.py` | ✅ 通读 |
| `gui/styled_dialog.py` | ✅ 通读 |
| `utils/config_mgr.py` / `exporter.py` / `autostart_mgr.py` | ✅ 通读 |
| `utils/paths.py` / `crypto.py` | ✅ 本轮新增 |
| `tests/test_calculator.py` | ✅ 本轮新增 |
| `NoOvertime.spec` | ✅ 通读 |
| `installer.iss` | ✅ 通读 |
| 6 个 `.bat` / `.vbs` 启动脚本 | ✅ 通读（见 E1） |
| 根目录 16 个 `test_*.py` / `inspect_*.py` 探针脚本 | ❌ **未审查** — 一次性调试脚本，不参与打包（`NoOvertime.spec` 只收 `main.py` 依赖链），建议直接归档到 `tools/` 或删除 |
| `scratch/test_tabs.py`、`test_tabs_dark.py` | ❌ **未审查** — 同上 |
| `EVE考勤与加班统计.spec`、`不加了.spec` | ❌ **未审查** — 旧项目遗留 spec |
| `ChineseSimplified.isl` | ❌ **未审查** — Inno Setup 官方中文语言包，无需改动 |
| `edgedriver.log` | ❌ **未审查** — 运行日志，建议加入 `.gitignore` |

> 结论：**参与实际运行与打包的代码 100% 通读**；未审查的均为不参与构建的历史遗留文件（也正是 D7 建议清理的对象）。
