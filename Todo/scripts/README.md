# script/ — 历史遗留归档

本目录存放**与当前 NoOvertime 主程序无关**的历史文件，仅作回溯用途。主程序运行、打包完全不需要它们。

> 目录迁移时间：2026-09-18（从项目根目录 / `scratch/` 整理而来）

## 目录说明

| 子目录 | 内容 | 说明 |
| --- | --- | --- |
| `probes/` | 18 个 `inspect_*.py` / `test_*.py` | 开发期的 Selenium 调试探针与 PyQt 界面探针，**无断言、非自动化测试**。正式测试见 `tests/` |
| `launchers/` | 6 个 `.bat` / `.vbs` | 历史启动脚本，多数指向已废弃的旧版本产物 |
| `legacy/` | 2 个旧项目 `.spec`、`test_export.xlsx`、旧 `config.json` | 旧项目构建脚本与遗留数据 |
| `logs/` | `edgedriver.log` | 早期运行日志 |

## ⚠️ 关于启动脚本（原 E1 问题）

迁移前这些脚本散落在项目根目录，其中 **4 个是坏的**，双击会启动旧版本程序或直接报错：

| 脚本 | 指向 | 状态 |
| --- | --- | --- |
| `launchers/启动EXE.bat` | `dist\EVE_App\EVE_App.exe` | ❌ 目录不存在，必然失败 |
| `launchers/启动程序.bat` | `dist\EVE考勤与加班统计\` | ⚠️ 旧项目 |
| `launchers/运行EXE.bat` → `启动EXE程序.vbs` | `dist\不加了\不加了.exe` | ⚠️ 旧项目 |
| `launchers/启动不加了.vbs` | 与上一个内容完全相同 | ⚠️ 重复文件 |
| `launchers/启动NoOvertime.vbs` | `dist\NoOvertime\NoOvertime.exe` | ✅ 可用（当前版本） |

**当前版本的正确启动方式：**

```bat
:: 方式一：直接运行打包产物
dist\NoOvertime\NoOvertime.exe

:: 方式二：源码启动（开发用，位于项目根目录）
启动软件.bat
```

## 运行探针脚本

所有探针都按「工作目录 = 项目根」的假设改写过路径（`../driver/msedgedriver.exe`），因此**必须从项目根目录执行**：

```bat
cd /d <项目根目录>
python script\probes\inspect_page.py
```

它们大多会启动一个带调试端口的 Edge 并打印页面结构，用于 HR 系统改版后重新定位选择器。建议确认不再需要后整体删除。
