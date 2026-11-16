# 本地 CAE 工具链（金属/塑料 · 静力 + 接触非线性 + 疲劳）

> 搭建时间：2026-11-11 ｜ 环境：Windows 11 ｜ 全部免费（开源优先）
> 目标链路：**FreeCAD 建模 → PrePoMax/CalculiX 求解（静力/接触）→ Python 疲劳评定**
>
> 工作区级约定（目录规范、单位制、验证基线、已知坑）见 `D:\E\Model\AGENTS.md`；
> 新建项目用 `tools\new_project.py <编号-名称>`，改环境后跑 `tools\regression_test.ps1` 回归。

## 三条硬性要求（摘要，完整见 `AGENTS.md` §0）

1. **遇到问题就提换工具建议（R1）**：任何环节出现「功能不支持 / 工具自身出错 / 被迫绕路 / 效率或精度到顶」，必须单开一节 `⚠️ 工具局限 / 换工具建议`，写全场景、受限能力、代价、替代方案、建议（现在换 / 以后换 / 不换），不许闷头绕过去。
2. **说「检查更新」就直接更新（R2）**：实测本地版本 → 联网查最新稳定版 → 备份/下载/替换 → 跑 `regression_test.ps1` → 更新本文件「变更记录」+ `AGENTS.md` §1 → commit → 报告。不做只报告等确认，不跳过回归。
3. **新项目第一步设 ASCII 网格工作目录（R3）**：`D:\E\Model\fem<编号>`，否则 Windows 版 Gmsh 必然 `Unable to open file`（中文路径按 GBK 解析），见 `AGENTS.md` §3.1。

## 目录结构

```
D:\E\Model\tools\
├─ PrePoMax\              # PrePoMax 3.0.0 绿色版（前后处理 + 内置 Gmsh/Netgen + CalculiX）
│  ├─ PrePoMax.exe        # 图形界面
│  ├─ PrePoMax.com        # 命令行/无窗口入口（脚本、批量）
│  ├─ Help\Python\        # 自带 Python API 文档 + MCP 使用指南（SKILL.md）
│  └─ Solver\             # ccx_dynamic.exe（已升级 CalculiX 2.23）+ MKL dll
├─ downloads\             # 安装包与 wheel 缓存
├─ 选材\
│  ├─ build_materials.py  # 从 FreeCAD 的 125 张 .FCMat 材料卡建库
│  ├─ materials.db        # SQLite：125 条材料（金属 103、热塑 13 等）
│  ├─ materials.csv       # 同内容 CSV，Excel 可直接打开
│  ├─ ashby_plots.py      # 画 E-ρ、σy-ρ Ashby 图
│  └─ ashby_*.png         # 已生成的图
├─ 疲劳\
│  ├─ frd_stress.py       # CalculiX .frd → 节点应力 CSV
│  └─ fatigue.py          # 高周疲劳：S-N + 平均应力修正 + Miner
├─ 测试\                  # 已验证的算例（cube_tension）
└─ python_libs\           # 可选 Python 库（rainflow 已装，fatpack/meshio 可选）
```

> 另有验证算例目录：`D:\E\Model\算例\带孔板\`（Kt 理论对比 + 网格收敛性，见其 README.md）

## 已验证（2026-11-11）

| 项目 | 状态 |
|---|---|
| CalculiX 2.22（FreeCAD 自带 `ccx.exe`） | ✅ 跑通 10×10×10 mm 立方体拉伸：SZZ=122.5 MPa（受端部约束影响），位移/应力输出正常 |
| **CalculiX 2.23**（替换进 PrePoMax Solver） | ✅ 版本横幅正确（2025-10-24 构建），同一算例结果与 2.22 **完全一致**（SZZ 122.496 / 77.4961 MPa） |
| `.frd` → 应力 CSV | ✅ 8 节点全部提取（`frd_stress.py`） |
| 疲劳评定 | ✅ UTS 400、R=0：σa=50.8 MPa → N=1.98e12，Miner 损伤 5e-6 |
| **带孔板 Kt 验证** | ✅ 3 套网格 Kt=2.42–2.44，理论 2.508，误差 −3%；网格收敛稳定（见 `算例\带孔板\README.md`） |
| PrePoMax 3.0.0 无窗口运行 | ✅ `PrePoMax.com --script ... -g No -x Yes --report run.json` 退出码 0，报告 JSON 正常 |
| 材料库 | ✅ 125 条材料入库，Ashby 图已生成 |
| FreeCAD 插件 | ✅ 已装入 `%APPDATA%\FreeCAD\v1-1\Mod`：Fasteners 0.5.67、SheetMetal 0.8.27、Supplemental-Materials 1.0.2（33 张追加材料卡）；SheetMetal 依赖 networkx 3.5 已补装 |

## 常用命令

### 1. 打开 PrePoMax（图形界面）
```
D:\E\Model\tools\PrePoMax\PrePoMax.exe
```

### 2. PrePoMax 无窗口跑脚本（批量/自动化）
```
D:\E\Model\tools\PrePoMax\PrePoMax.com --script D:\path\to\job.py -g No -x Yes ^
    -w D:\E\Model\tools\测试\pmx_work --report D:\E\Model\tools\测试\run_report.json
```
> 脚本是 PrePoMax Python API（见 `PrePoMax\Help\Python\Python_API_Overview.html`），
> 应用内置 Python 3.12，无需额外安装。GUI 里 **Tools → Automation Server** 还可开 MCP 端点供 AI 调用。

### 3. 重新生成材料库 / Ashby 图
```
F:\FreeCAD\bin\python.exe "D:\E\Model\tools\选材\build_materials.py"
F:\FreeCAD\bin\python.exe "D:\E\Model\tools\选材\ashby_plots.py"
```
> 数据库字段：`density_kg_m3, E_GPa, nu, yield_MPa, uts_MPa, cte_1_K, k_W_mK`；
> 疲劳字段 `sigma_f_MPa, b, Se_MPa` 默认空，按实测/厂商 S-N 数据填写。

### 4. 疲劳流程（例子：cube_tension）
```
F:\Python3.13.13\python.exe "D:\E\Model\tools\疲劳\frd_stress.py" cube_tension.frd
F:\Python3.13.13\python.exe "D:\E\Model\tools\疲劳\fatigue.py" cube_tension_stress.csv --uts 400 --ratio 0 --method goodman
```
恒幅：`--ratio` 是应力比 R；变幅：加 `--spectrum spectrum.csv`（两列 `scale,n_cycles`）。
`--method` 可选 `goodman|gerber|swt|none`；有 Basquin 参数时用 `--sigma-f --b`，或 `--material 名称` 从 materials.db 读。

## 待办 / 可选

1. **重启 FreeCAD**，确认工作台下拉里出现 **Fasteners** 和 **SheetMetal**；材料对话框里能看到 Supplemental-Materials 的追加材料卡。
2. **ccx2paraview**（可选）：`.frd` → `.vtu`，给 ParaView/Python 后处理；不装也能用 `frd_stress.py`。
3. **疲劳数据**：金属用厂商 S-N/Shigley 估算；塑料用 CAMPUS（https://www.campusplastics.com/campus/en）或厂商 datasheet。
4. **可选 Python 库**：`python_libs\` 目前只有 `rainflow`（雨流计数，已可用）；
   `fatpack` / `meshio` 因当前网络（PyPI 文件主机 SSL 超时/403）未装，属**可选项**——
   疲劳主流程不依赖它们：`fatigue.py` 只用 numpy（系统已有）、`frd_stress.py` 只用标准库。
   需要时可用镜像安装：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --target tools\python_libs fatpack meshio`。
5. **CFD 工具链（暂缓，2026-11-14 决定不做）**：CfdOF 1.37.3 已装，但 OpenFOAM 求解器（blueCFD-Core 2024-1，安装包 `downloads\blueCFD-Core-2024-1-win64-setup.exe`，1.15 GB）与 ParaView 6.1.0 都**没装**；cfMesh/HiSA 因 SourceForge 全部 403 未取。要继续时按 `文档\工具链调研-2026-11.md` §10 的步骤和踩坑记录走（关键：安装前把 `$env:TMP`/`$env:TEMP` 指到非 C 盘再静默安装）。

## FreeCAD 插件（已安装）

| 插件 | 版本 | 位置 | 依赖 |
|---|---|---|---|
| Fasteners | 0.5.67 | `%APPDATA%\FreeCAD\v1-1\Mod\Fasteners` | 无 |
| SheetMetal | 0.8.27 | `%APPDATA%\FreeCAD\v1-1\Mod\SheetMetal` | networkx 3.5（已装到 `AdditionalPythonPackages\py311`） |
| Supplemental-Materials | 1.0.2 | `%APPDATA%\FreeCAD\v1-1\Mod\Supplemental-Materials` | FreeCAD Material（内置） |
| CfdOF（⚠️ 当前不可用） | 1.37.3 | `%APPDATA%\FreeCAD\v1-1\Mod\CfdOF` | 需要 OpenFOAM（blueCFD-Core）+ ParaView，**均未安装**；用户 2026-11-14 决定 CFD 暂缓 |

安装脚本：`tools\install_addons.py`、`tools\install_sheetmetal_dep.py`（重装/更新时可复用）。
`parts_library`（FreeCAD-library）按评估结论**未安装**：5.6 GB 且 Windows 路径有 bug，按需下单个 STEP。

## 注意事项

- 单位制：模型与材料统一用 **mm-N-MPa**；PrePoMax 新建模型时确认 unit system。
- 接触非线性：先保证收敛，再做网格加密验证（接触压力对网格敏感）。
- 疲劳：S-N 数据离散大，结果用于相对比较/初筛，关键件必须试验验证。
- 塑料：PrePoMax 只有线弹性 + 弹塑性材料模型，**不支持黏弹性/蠕变**。

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-11 | 初始搭建：FreeCAD 1.1.4 + 3 插件、Gmsh 4.15.0、PrePoMax 3.0.0（CalculiX 2.23）、材料库、疲劳脚本 |
| 2026-11-14 | 工作区改名 `D:\E\项目` → `D:\E\Model`，脚本/文档路径全量同步（回归 5/5 通过）；安装 CfdOF 1.37.3（缺 OpenFOAM，不可用）；blueCFD-Core 2024-1 安装到 3.2 GB 时按用户要求中止（安装器自动回滚，无残留），ParaView 6.1.0 msi 下载中止后删除 |
| 2026-11-16 | **新增 `AGENTS.md` §0 三条硬性要求（R1 换工具建议 / R2 检查更新自动执行 / R3 中文路径新项目第一步）**，本文档顶部同步摘要；工具链版本无变化（FreeCAD 1.1.4 / PrePoMax 3.0.0 / CalculiX 2.23 / Gmsh 4.15.0 均为当前最新稳定版，无需更新） |
