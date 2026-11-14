# 工作区说明（给 AI 代理）

本工作区 `D:\E\Model` 用于 **CAD 建模 + 有限元分析**。所有建模/网格/FEA 任务都在这里进行。
人类可读的入口见 `README.md`；本文件记录约定、路径、命令和已知坑，供后续会话直接复用。

## 1. 工具链（已安装，不要重复安装）

| 用途 | 路径 | 版本 |
|---|---|---|
| 建模（GUI） | `F:\FreeCAD\bin\freecad.exe` | FreeCAD 1.1.4 |
| 建模（命令行） | `F:\FreeCAD\bin\freecadcmd.exe` | 同上（Part 模块可用；**Part.export 无界面导出会崩溃，导 STEP 用 Gmsh 或 GUI**） |
| 网格 | `F:\FreeCAD\bin\gmsh.exe` | Gmsh 4.15.0（OCC 内核，可 `-0 -format stp` 导 STEP、`-3 -format inp` 出 Abaqus/CalculiX 网格） |
| 前处理/求解 GUI | `D:\E\Model\tools\PrePoMax\PrePoMax.exe` | PrePoMax 3.0.0 |
| 求解器 | `D:\E\Model\tools\PrePoMax\Solver\ccx_dynamic.exe` | CalculiX **2.23**（已替换；旧 2.22 备份为 `.2.22.bak`） |
| 命令行求解（备用） | `F:\FreeCAD\bin\ccx.exe` | CalculiX 2.22 |
| Python（系统） | `F:\Python3.13.13\python.exe` | 3.13，含 numpy/matplotlib；无 pandas/scipy |
| Python（FreeCAD） | `F:\FreeCAD\bin\python.exe` | 3.11，含 numpy/pandas/scipy/matplotlib/yaml（做材料库/画图用这个） |
| 可选库 | `tools\python_libs\`（rainflow 等） | 脚本已自动加入 sys.path |
| CFD 插件（已装，**无求解器**） | `%APPDATA%\FreeCAD\v1-1\Mod\CfdOF` | CfdOF v1.37.3（纯 Python，6 MB）；首选项 `InstallationPath=F:\blueCFD-Core` 指向**不存在**的目录 |

**CFD 状态（2026-11-14）**：用户决定**暂不做流体仿真**，blueCFD-Core 2024-1 与 ParaView 6.1.0 **未安装**（安装包留在 `tools\downloads\blueCFD-Core-2024-1-win64-setup.exe`，1.15 GB，可删）。CfdOF 插件保留但当前不可用（`CfdTools.getFoamRuntime()` 会抛 `OSError: The directory F:\blueCFD-Core is not a recognised OpenFOAM installation`）。将来要装时的踩坑记录见 `文档\工具链调研-2026-11.md` §10。

PrePoMax 自带 **Python API + 命令行 + MCP 自动化端点**（`tools\PrePoMax\Help\Python\`）。
无窗口跑脚本：
```
tools\PrePoMax\PrePoMax.com --script <绝对路径.py> -g No -x Yes -w <工作目录> --report <报告.json>
```

## 2. 单位制（硬性约定）

- 统一 **mm-N-MPa**（长度 mm，力 N，应力 MPa，密度 t/mm³，即 7.85e-9 for steel）。
- 模型、材料、载荷、结果全部同一套单位；报告里写明单位。
- 材料库里密度是 kg/m³（建库原始值），做 FEA 时换算（钢 7850 kg/m³ = 7.85e-9 t/mm³）。

## 3. 目录约定

```
D:\E\Model\
├─ AGENTS.md            # 本文件
├─ README.md            # 人类入口
├─ 项目\                # 实际项目，一个项目一个目录：<编号-名称>\
│  ├─ 01-几何\          # .FCStd / .STEP
│  ├─ 02-网格\          # .geo / .inp / .msh
│  ├─ 03-计算\          # .inp / .pmx / 求解日志
│  ├─ 04-结果\          # .frd / 云图 / .csv
│  └─ 05-报告\          # 计算书/结论
├─ 算例\                # 已验证的基准算例（回归用，不要乱改）
├─ tools\               # 工具链安装目录 + 通用脚本（材料库/疲劳/安装脚本）
├─ 文档\                # 规范、笔记、学习资料
└─ 归档\                # 完结/废弃项目
```

新建项目：`F:\Python3.13.13\python.exe tools\new_project.py <编号-名称>`（自动按模板建目录）。

## 4. 通用脚本（复用，不要重写）

| 脚本 | 作用 |
|---|---|
| `tools\选材\build_materials.py` | 从 FreeCAD 125 张 .FCMat 重建 `materials.db`（FreeCAD Python 跑） |
| `tools\选材\ashby_plots.py` | 画 E-ρ / σy-ρ Ashby 图 |
| `tools\疲劳\frd_stress.py` | CalculiX `.frd` → 节点应力 CSV（纯标准库） |
| `tools\疲劳\fatigue.py` | 高周疲劳：S-N（Basquin 或 Shigley 估算）+ 平均应力修正 + Miner；支持恒幅/谱载荷 |
| `tools\new_project.py` | 一键新建项目目录 |
| `tools\regression_test.ps1` | 回归测试（ccx 版本、立方体、Kt、疲劳），更新工具后跑 |
| `算例\带孔板\run_kt.py` | 带孔板 Kt 全自动验证（网格→求解→理论对比） |

## 5. 验证基线（回归时必须一致）

| 算例 | 基线结果 |
|---|---|
| 立方体拉伸（`tools\测试\cube_tension.inp`） | CalculiX 2.22 与 2.23 结果一致：SZZ=122.496 / 77.4961 MPa |
| 带孔板 Kt（`算例\带孔板`） | Kt_net = 2.42–2.44（理论 2.508，误差 −3%，已网格收敛） |
| 疲劳脚本（同算例应力） | UTS 400、R=0：σa=50.84 MPa → N=1.98e12，损伤 5.04e-6 |
| 悬臂梁全流程（`项目\001-悬臂梁静力分析`） | 碳钢 100×10×10 mm、端部 100 N：δ=0.19043 mm（理论 0.19048）、跨中 30.03 MPa（理论 30）、固定端最大 59.31/全场 60.88 MPa（理论 60）；ccx 2.22 与 2.23 结果一致 |
| L 形支架全流程（`项目\002-L形支架静力分析`） | 底板 100×60×8 + 立板 8×60×80 + R8 + 4×Ø9、顶面 500 N 沿 −X：顶面挠度 0.1525 mm（手算 0.1587，−3.6%）、全场最大 61.68 MPa @ R8 圆角（手算 62.5，−1.3%）、SF=235/61.7=3.8；C3D10 36325 节点、95100 方程 |

## 6. 已知坑（都是踩过的，别再踩）

1. **CalculiX 面压力**：`*DLOAD` 必须写 `P1`~`P6` + 元素号（如 `191, P1, -100.`）；只写 `P` 会让 ccx 崩溃（0xC0000005）且不报错。
2. **不要用节点力（`*CLOAD`）模拟均布拉伸**：会在加载面边缘产生虚假应力集中（本例曾算出 525 MPa 而不是 ~300）。
3. **FreeCAD 命令行导 STEP（Part.export/exportStep）会崩溃**：几何用 Gmsh `.geo` 建；或让用户在 GUI 里导出。
4. **Gmsh 语法**：`BooleanDifference(3) = {...}` 必须带 `=`；`Cylinder` 是 `{x,y,z,dx,dy,dz,r}` 七个参数（第 8 个是角度，不是高度）。
5. **matplotlib**：受限环境写不了 `C:\Users\...\.matplotlib`，脚本里要设 `MPLCONFIGDIR` 到工作区。
6. **pip 在本机沙箱会失败**：装 Python 库用 `--target tools\python_libs` 或直接解压 wheel；PyPI 文件主机偶发 SSL 超时/403，可用清华镜像或 GitHub codeload 源码。
7. **GitHub 下载**：`codeload.github.com` 直连可用，`github.com/.../archive` 会重置；失败时加代理 `127.0.0.1:30912`（GitHubPP，仅 GitHub 域名）。
8. **FreeCAD 的附加组件管理器**已设为「无代理」（`proxy_type=none`），不要改回 system，否则 addons.freecad.org 会被 GitHubPP 返回 403。
9. **插件**：Fasteners / SheetMetal / Supplemental-Materials 装在 `%APPDATA%\FreeCAD\v1-1\Mod`；SheetMetal 依赖 networkx 3.5（装在 `AdditionalPythonPackages\py311`）。不要装 `parts_library` 整包。
10. **FreeCAD 1.1 的力方向**：`ConstraintForce.Direction` 是 PropertyLinkSub（指向一条边），不是向量；GUI「方向」框填 `(0,0,-1)` 会报 Invalid syntax，Python 里赋 `App.Vector` 会报 TypeError。正确写法：`cf.Direction=(obj,["Edge1"]); cf.Reversed=True`（选一条与目标方向平行的边）。官方示例见 `F:\FreeCAD\Mod\Fem\femexamples\ccx_cantilever_faceload.py`。
11. **FreeCAD 1.1 后处理按 SI 单位显示**：位移是 m、应力是 Pa（色标 1.910e-04 = 0.191 mm，6.088e+07 = 60.88 MPa）；`.frd` 内仍是 mm-N-MPa，解析不受影响。
12. **FreeCAD FEM 求解工作目录默认在系统临时目录**（`C:\Users\...\AppData\Local\Temp\fcfem_*`，沙箱读不了）：求解器面板里把「工作目录」改到项目 `03-计算\`，否则结果文件无法归档。注意：若 FEM 偏好里勾了「使用临时目录」，会覆盖对象的 WorkingDirectory；正确做法是设置偏好键（见第 15 条）。
13. **Gmsh 不支持中文路径**：FreeCAD→Gmsh 用 UTF-8 传 `shape2mesh.geo` 路径，Windows 版 Gmsh 按 ANSI 解析，路径/文件名含中文就报 `Unable to open file 'D:/E/ÏîÄ¿/...'`（日志面板还会因 GBK 解码失败抛 UnicodeDecodeError，掩盖真实原因）。对象内部 Name 在 1.1 里只读、无法改；解决：复制成 ASCII 名 Part::Feature（`b=addObject('Part::Feature','Bracket'); b.Shape=s`）再网格化，或使用 ASCII 工作目录。
14. **Python 给 Force/Boundary 赋数值必须带单位字符串**：Calc 内部单位是 `kg·mm/s²`（= mN），`cf.Force = 500` 表示 500 mN = 0.5 N，结果整体小 1000 倍；写 `cf.Force = '500 N'`（GUI 输入会自动换算，不受影响）。
15. **FEM 偏好键**：求解器二进制 `User parameter:BaseApp/Preferences/Mod/Fem/Ccx` → `ccxBinaryPath`（不设会得到相对路径 `.\ccx.EXE`，启动即退出）；工作目录 `.../Fem/General` → `UseBesideDirectory` / `UseCustomDirectory` / `CustomDirectoryPath` / `UseTempDirectory`。
16. **对象内部 Name ≠ Label**：`App.ActiveDocument.getObject()` 只认内部 Name（连字符会被换成下划线，如 `Force-Top` → `Force_Top`），Label 是界面显示名；调试时先打印 `[(o.Name,o.Label) for o in doc.Objects]`。
17. **Inno Setup 安装器（blueCFD 这类 1 GB+ 的 .exe）静默安装的坑**：它默认把解包临时文件放 `%TEMP%`（本机在 C 盘），实测会出现「进程一闪而过、无日志、无安装目录、cmd 里 `%ERRORLEVEL%` 还显示 0」的假失败/假成功。正确做法：先把 `$env:TMP`/`$env:TEMP` 指到**目标盘**（例如 `D:\E\Model\tools\tmp\itmp`）再 `Start-Process -Wait`，并加 `/LOG=<非 C 盘路径>`；运行时还要用 `-RedirectStandardOutput/-RedirectStandardError` 重定向，否则安装器子进程继承管道句柄会让调用永远不返回。1.15 GB 的包解压约 5–8 分钟、落盘约 3.2 GB / 8.9 万文件。
18. **不要把下载包或安装临时文件写到 C 盘**（用户明确要求）：安装包统一放 `tools\downloads\`，临时目录放 `tools\tmp\`；`.msi` 用 `msiexec /a <msi> /qn TARGETDIR=<非 C 盘路径>` 做管理安装（只解包，不需要管理员权限）。

## 7. 更新策略与「检查更新」标准动作

基本策略：

- 只跟**稳定版**，不用预发布/周构建/主版本大改（除非用户明确要求）。
- 更新后必须跑 `tools\regression_test.ps1` 且全绿；失败就回滚刚更新的组件。
- PrePoMax 更新会重置 `Solver\` 目录 → 更新后必须重新替换成 CalculiX 2.23。
- 更新完成后把版本号写回本文件 §1 和 `tools\README.md`，并 git commit。

**当用户说「检查更新」/「更新工具」/「看看有没有新版本」时：不要反问，直接执行下面完整流程，自行完成更新。**

### 7.1 检查本地当前版本

| 组件 | 检查命令 |
|---|---|
| FreeCAD | `F:\FreeCAD\bin\freecadcmd.exe -c "import FreeCAD;print(FreeCAD.Version())"`（或看安装目录/文件版本） |
| PrePoMax | `tools\PrePoMax\PrePoMax.exe` 文件版本；或启动后标题栏 |
| CalculiX | `tools\PrePoMax\Solver\ccx_dynamic.exe -v` |
| Gmsh | `F:\FreeCAD\bin\gmsh.exe --version` |
| 插件 | `%APPDATA%\FreeCAD\v1-1\Mod\<插件>\package.xml` 或 `__init__.py` 中的版本号 |
| networkx | `%APPDATA%\FreeCAD\v1-1\AdditionalPythonPackages\py311\networkx\__init__.py` |
| 可选库 | `tools\python_libs\`（rainflow 等） |

### 7.2 联网查最新稳定版（必须实际查，不许凭记忆）

| 组件 | 查询地址 |
|---|---|
| FreeCAD | GitHub `FreeCAD/FreeCAD` releases / freecad.org（只取正式版，跳过 weekly、rc） |
| PrePoMax | https://prepomax.fs.um.si/ 下载页（或 GitHub releases） |
| CalculiX | http://www.dhondt.de/ 的 Windows 版 |
| Gmsh | https://gmsh.info/ 或 GitHub releases |
| Fasteners | https://github.com/shaise/FreeCAD_FastenersWB/releases |
| SheetMetal | https://github.com/shaise/FreeCAD_SheetMetal/releases |
| Supplemental-Materials | https://github.com/FreeCAD/Supplemental-Materials |
| networkx | PyPI |

下载途径与代理处理见 §6 第 6、7 条（codeload 直连、PyPI 镜像、GitHubPP 仅代理 GitHub）。

### 7.3 有更新就直接更新（备份 → 下载 → 替换 → 验证）

1. **先备份**：旧目录改名 `<xxx>.bak` 或打包到 `归档\更新备份\`。
2. **FreeCAD**：大版本更新前备份 `%APPDATA%\FreeCAD`（配置/插件/材料卡都在这）；更新后重跑 `tools\选材\build_materials.py` 重建材料库。
3. **PrePoMax**：新 zip 覆盖 `tools\PrePoMax\`，随后把 `Solver\ccx_dynamic.exe` 重新替换为 CalculiX 2.23（旧文件保留 `.bak`），确认 MKL dll 齐全。
4. **CalculiX**：只换 `Solver\ccx_dynamic.exe`，旧版留 `.bak`。
5. **FreeCAD 插件**：优先改成 git clone 后 `git pull`；目前是 zip 装法，则下载 release zip 覆盖 `Mod\<插件>\`。
6. **networkx**：wheel/源码装到 `AdditionalPythonPackages\py311`。
7. 没有新版本就跳过，不要硬装。

### 7.4 回归验证

```powershell
powershell -ExecutionPolicy Bypass -File D:\E\Model\tools\regression_test.ps1
```

必须 5/5 全通过。失败则回滚刚更新的组件（用备份），并记录失败原因。

### 7.5 收尾（每次必做）

1. 更新本文件 §1 版本表和 `tools\README.md` 的版本记录；
2. `git add -A; git commit -m "更新：<组件> x.y -> x.z（回归通过）"`；
3. 向用户报告：检查了哪些、旧/新版本、跳过了哪些及原因、回归结果。

### 7.6 判断标准

- **值得更新**：安全/崩溃修复、当前版本有 bug、需要新功能。
- **可选**：仅补丁号变化且与本工作流无关 → 说明后跳过。
- **默认不更**：预发布、周构建、主版本大改 → 除非用户明确要求。


## 8. 输出习惯

- 每个项目最终在 `05-报告` 留一份 `.md` 计算书：模型概述、材料及来源、边界/载荷、网格与收敛性、关键结果、结论与假设。
- 结果数据（.frd/.csv/云图）放 `04-结果`；中间文件放 `03-计算`。
- 材料来源必须记录（牌号、标准、数据出处），疲劳用到的 S-N 参数单独注明来源。
