# 不加了 (NoOvertime) ☕

> **智能考勤打卡与加班工时统计助手**  
> 专为日常考勤审核与加班工时核算打造的高效自动化工具。基于原生 Microsoft Edge 浏览器与 CDP 协议，支持一键采集考勤记录、智能计算有效加班工时、平滑防休眠、多主题切换与一键导出报表。

---

## 📦 版本发布与下载 (Releases)

本项目同时提供 **Edge 152 专用版本** 与 **通用版本（内置 152/153 双驱动动态适配）**：

| 版本类型 | 文件路径 | 适用场景 | 说明 |
| :--- | :--- | :--- | :--- |
| **🚀 Edge 152 安装版 (推荐)** | [`release/NoOvertime_Setup_x64_Edge152.exe`](release/NoOvertime_Setup_x64_Edge152.exe) | 电脑 Edge 版本为 152.x，高频使用 | 专为 Edge 152.0.4191.53 优化构建，具备安装向导，桌面/托盘快捷方式，智能防多开。 |
| **💼 Edge 152 便携版** | [`release/NoOvertime_Portable_x64_Edge152.zip`](release/NoOvertime_Portable_x64_Edge152.zip) | 电脑 Edge 版本为 152.x，免安装体验 | 绿色免安装，解压后双击 `NoOvertime.exe` 即可直接使用，不写注册表。 |
| **🌟 通用安装版 (双驱动兼容)** | [`release/NoOvertime_Setup_x64.exe`](release/NoOvertime_Setup_x64.exe) | 自动适配 Edge 152 / 153 或自动更新 | 内置 152 + 153 动态驱动调度引擎，并支持未匹配时静默从微软官方源下载驱动。 |
| **💼 通用便携版 (双驱动兼容)** | [`release/NoOvertime_Portable_x64.zip`](release/NoOvertime_Portable_x64.zip) | 跨设备免安装使用 | 解压即用，自动检测宿主机 Edge 版本并加载匹配驱动。 |

---

## ✨ 核心特性

1. **智能日历扫描与详情提取**
   - **拟人化节奏保护**：点击日历格并获取数据后稳定展示 2 秒再关闭，彻底杜绝短时高频访问，避免触发企业 WAF / 防爬风控报警。
   - **智能跳过机制**：未来未发生日期、无打卡且无加班申请的公休周末自动跳过，无需打开弹窗抽屉，节省全月 80% 无效耗时。
   - **严格回读核验**：日期选择器派发事件后严格校验页面显示月份区间，杜绝静默抓错月份。

2. **工时核算引擎**
   - 支持工作日延时加班（默认 18:00 起计，可自定义起计时间与基准下班时间）。
   - 支持周末、法定节假日申请单加班核算。
   - 支持最小起算时长（默认 30 分钟）与颗粒度（30 分钟步进舍入）。
   - 支持跨天最晚截断时间（次日 02:00），杜绝忘打卡异常数据失真。

3. **原生 Edge CDP 会话复用**
   - 调用本机原生系统 Microsoft Edge（真内核、真实指纹、真实企业 SSO 会话）。
   - 支持自动复用浏览器已登录态，无需重复输入双因子验证码。

4. **精致桌面交互**
   - **双主题随心切换**：赛博朋克深色（Cyberpunk Dark）与清爽商务浅色（Modern Light）。
   - **平滑防休眠保持**：利用 Windows API 抑制息屏与休眠，保障后台采集不断连。
   - **智能托盘常驻**：后台最小化至托盘，状态通知提示，支持全局单实例互斥防多开。
   - **报表一键导出**：支持一键导出包含考勤日期、星期、班次、打卡时间、加班工时、规则备注的 Excel (.xlsx) / CSV 文件。

---

## 🛠️ 项目结构

```text
tools/
├── release/                        # 正式发布文件目录
│   ├── NoOvertime_Setup_x64.exe    # 🚀 64位独立安装程序
│   ├── NoOvertime_Portable_x64.zip # 💼 免安装绿色便携包
│   └── RELEASE_NOTES.md            # 发布说明与更新日志
├── Todo/                           # 源代码工程目录
│   ├── core/                       # 核心业务逻辑 (采集器、工时计算器、Edge CDP 管理)
│   ├── gui/                        # PyQt5 现代化界面 (主窗口、日历视图、设置面板)
│   ├── utils/                      # 工具库 (配置管理、开机自启、防休眠、日志系统)
│   ├── driver/                     # Edge WebDriver 驱动
│   ├── img/                        # 界面图标与设计资源
│   ├── tests/                      # 单元测试集
│   ├── main.py                     # 程序主入口
│   ├── installer.iss               # Inno Setup 安装包构建脚本
│   └── NoOvertime.spec             # PyInstaller 打包规格文件
└── README.md                       # 项目说明文档
```

---

## 🚀 开发者快速上手

### 1. 环境准备
推荐使用 **Python 3.10 ~ 3.13**：
```bash
cd Todo
pip install -r requirements.txt
```

### 2. 本地运行测试
```bash
# 启动程序
python main.py

# 运行工时核算单元测试
python -m pytest tests/
```

### 3. 编译发布版本
```powershell
# 1. 使用 PyInstaller 编译绿色目录
python -m PyInstaller NoOvertime.spec --noconfirm

# 2. 同步静态资源
Copy-Item -Recurse -Force driver, img dist\NoOvertime\

# 3. 编译 Inno Setup 安装程序
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# 4. 压缩制作便携版
Compress-Archive -Path "dist\NoOvertime" -DestinationPath "release\NoOvertime_Portable_x64.zip" -Force
```

---

## 📄 开源许可与声明
本项目仅用于个人出勤与加班工时合规统计辅助，遵循合法合规使用原则。
