# 建模 + 有限元分析工作区

`D:\E\项目` 是本人的 **CAD 建模与有限元分析（FEA）** 工作区。以后所有建模、网格、求解、后处理任务都在这里进行。

## 目录

```
D:\E\项目\
├─ README.md            ← 本文件
├─ AGENTS.md            ← AI 代理用的工作区约定（工具链/单位制/坑/基线）
├─ 项目\                ← 实际项目，一个项目一个目录
│  ├─ _模板\            ← 项目模板（new_project.py 会复制它）
│  └─ <编号-名称>\      ← 01-几何 / 02-网格 / 03-计算 / 04-结果 / 05-报告
├─ 算例\                ← 已验证的基准算例（回归测试用）
│  └─ 带孔板\           ← 应力集中 Kt 验证（Kt≈2.43，理论 2.508）
├─ tools\               ← 工具链安装目录 + 通用脚本
│  ├─ PrePoMax\         ← PrePoMax 3.0.0（含 CalculiX 2.23 求解器）
│  ├─ CalculiX-2.23\    ← CalculiX 官方 2.23 原始解压
│  ├─ 选材\             ← 材料数据库 materials.db + Ashby 图
│  ├─ 疲劳\             ← .frd 应力提取 + 高周疲劳评定
│  ├─ 测试\             ← 立方体基准算例
│  ├─ downloads\        ← 安装包/wheel 缓存（可删）
│  ├─ install_*.py      ← 一键安装脚本（PrePoMax/CalculiX/插件/依赖）
│  ├─ new_project.py    ← 新建项目目录
│  └─ regression_test.ps1 ← 环境回归测试
├─ 文档\                ← 调研报告、规范、学习笔记
└─ 归档\                ← 完结/废弃项目与调试中间文件
```

## 工具链（均已安装）

| 环节 | 工具 |
|---|---|
| 建模 | FreeCAD 1.1.4（GUI），插件：紧固件 / 钣金 / Supplemental-Materials |
| 网格 | Gmsh 4.15.0（FreeCAD 自带）、PrePoMax 网格器 |
| 前处理 + 求解 | PrePoMax 3.0.0 + CalculiX 2.23（静力、接触非线性、模态…） |
| 后处理 | PrePoMax、Python（应力提取、云图、疲劳评定） |
| 材料 | FreeCAD 125 张材料卡 → `tools\选材\materials.db` + 33 张 Supplemental 卡 |

全部免费开源；版本已锁定（见 `AGENTS.md` §7）。

## 快速开始

### 1. 新建项目

```powershell
F:\Python3.13.13\python.exe D:\E\项目\tools\new_project.py 001-支架强度校核
```

自动生成 `项目\001-支架强度校核\` 及 `01-几何` ~ `05-报告` 五个子目录和项目 README（待填）。

### 2. 建模 / 网格

- **GUI 建模**：打开 `F:\FreeCAD\bin\freecad.exe`，建完后导出 `.STEP` 到 `01-几何`。
- **批量/脚本建模**：用 Gmsh `.geo`（`F:\FreeCAD\bin\gmsh.exe`，OCC 内核），几何、网格一步出。
- **网格**：Gmsh 出 `-3 -order 2 -format inp` 的 C3D10，或 PrePoMax 里几何导入+划网。

### 3. 求解

**方式 A：PrePoMax（推荐，有 GUI）**

打开 `tools\PrePoMax\PrePoMax.exe` → 导入几何 → 材料（可直接用 Supplemental 卡或手输）→ 接触/约束/载荷 → Run。求解器默认就是 CalculiX 2.23。

**方式 B：命令行（批量/可复现）**

```powershell
& 'D:\E\项目\tools\PrePoMax\Solver\ccx_dynamic.exe' -i 模型.inp
```

**方式 C：PrePoMax 脚本（无窗口自动化）**

```powershell
& 'D:\E\项目\tools\PrePoMax\PrePoMax.com' --script build.py -g No -x Yes -w 输出目录 --report 报告.json
```

### 4. 后处理

- **云图/位移**：PrePoMax 里看，或把 `.frd` 转 VTK（ccx2paraview / meshio）。
- **应力提取**：

```powershell
F:\Python3.13.13\python.exe D:\E\项目\tools\疲劳\frd_stress.py 结果.frd -o 应力.csv
```

- **疲劳评定**（高周，S-N + Miner）：

```powershell
F:\Python3.13.13\python.exe D:\E\项目\tools\疲劳\fatigue.py 应力.csv --uts 400 --ratio 0
```

## 材料选择

`tools\选材\materials.db` 收录 FreeCAD 自带 125 张材料卡（金属 103 / 塑料 13 / 其他 9），含 E、ν、屈服、抗拉、密度、热膨胀、导热。

- 查看/筛选：任何 SQLite 工具打开；或 `python -c "import sqlite3;..."`。
- Ashby 图：`tools\选材\ashby_E_rho.png`、`ashby_sy_rho.png`（选材用刚度/强度-密度图）。
- 重建：`F:\FreeCAD\bin\python.exe tools\选材\build_materials.py`。

## 验证基线（改环境后先跑这个）

```powershell
powershell -ExecutionPolicy Bypass -File D:\E\项目\tools\regression_test.ps1
```

覆盖：CalculiX 版本、立方体单单元、带孔板 Kt（2.42–2.44）、疲劳脚本。全绿才说明工具链正常。

## 约定（摘要，完整见 AGENTS.md）

- **单位制**：mm-N-MPa（密度 t/mm³，钢 7.85e-9）。
- **每个项目**：几何/网格/计算/结果/报告分开；最终在 `05-报告` 写 `.md` 计算书。
- **材料来源**：记录牌号+标准+数据出处；疲劳参数单独注明来源。
- **不要**随便更新工具链（会破坏已验证基线）；更新前看 `AGENTS.md` §7。
- **说「检查更新」时**：我会检查本工作区全部工具（FreeCAD、PrePoMax、CalculiX、Gmsh、插件、networkx 等）的版本，联网对比最新稳定版并**自行完成更新**，最后跑回归测试——无需你再确认（除非涉及主版本大改/预发布）。流程见 `AGENTS.md` §7。

## 文档

- `文档\`：工具链调研报告、后续补充的规范/笔记。
- `AGENTS.md`：工具链、命令、已知坑（9 条，含 CalculiX `P1`~`P6`、Gmsh 语法、FreeCAD 导 STEP 崩溃等）。
- `算例\带孔板\README.md`：Kt 验证完整过程，可作为"照着做"的模板。
