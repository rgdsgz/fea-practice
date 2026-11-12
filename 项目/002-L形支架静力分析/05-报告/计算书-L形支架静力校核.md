# 002 — L 形支架静力校核计算书

- 项目：002-L形支架静力分析
- 日期：2026-11-12
- 单位制：**mm–N–MPa**（密度 kg/m³ 仅用于材料卡，FEA 中自动换算）
- 分析类型：线性静力（小变形）

---

## 1. 目的与验收判据

校核钣金式 L 形支架在立板顶部 500 N 侧向载荷下的强度与刚度。

| 项目 | 判据 |
|---|---|
| 材料 | CalculiX-Steel（E=210 GPa，ν=0.30，ρ=7900 kg/m³） |
| 屈服强度 σy | 235 MPa（普通结构钢取值，作为本算例判据） |
| 安全系数 | SF = σy / σ_max ≥ **2.0**（即 σ_max ≤ 117.5 MPa） |
| 刚度 | 自由端位移 ≤ 1.0 mm（本算例自定） |

## 2. 几何

- 底板：100 (X) × 60 (Y) × 8 (Z)
- 立板：8 (X) × 60 (Y) × 80 (Z)，位于 x = 0~8、z = 8~88
- 内角过渡圆角 **R8**（立板内侧面 x=8 与底板上表面 z=8 之间）
- 底板 4 个 **Ø9** 通孔：(25,20)、(75,20)、(25,40)、(75,40)
- 整体外形：100 × 60 × 88 mm

建模（FreeCAD 1.1.4，Part 工作台）：Box(100,60,8) + Box(8,60,80)（Placement z=8）→ 布尔并集 → Part::Fillet（内角边 R8）→ 4 个 Ø9 圆柱布尔差。
几何文件：`01-几何\L形支架.FCStd`。

## 3. 材料

| 项目 | 数值 | 来源 |
|---|---|---|
| 名称 | CalculiX-Steel | FreeCAD 标准材料卡（`data/Mod/Material/Resources/Materials/Standard/Metal/Steel/CalculiX-Steel.FCMat`） |
| E | 210 000 MPa | 同上 |
| ν | 0.30 | 同上 |
| ρ | 7900 kg/m³ | 同上 |
| σy | 235 MPa | 普通结构钢典型值（假设，材料卡本身不含塑性数据） |

> 仅做线弹性分析，未输入塑性段；若需极限承载/塑性重分布，应改用 PrePoMax + 弹塑性材料。

## 4. 网格

- 工具：FreeCAD FEM 内置 Gmsh（4.15.0）
- 单元：**C3D10 二阶四面体**，单元维度 From Shape
- 尺寸：最大 3.0 mm，最小 0.5 mm（圆角曲率处自动加密）
- 规模：**节点 36 325**，体积单元约 20 690，自由度数 **95 100**
- 备注：几何以 ASCII 命名的 `Bracket`（Part::Feature 副本）参与网格化——FreeCAD→Gmsh 传参为 UTF-8，中文路径/中文对象名会导致 Gmsh 打不开文件（见 §10 坑 1）

## 5. 边界与载荷

| 项目 | 位置 | 数值 |
|---|---|---|
| 约束 | 底面 z=0（Bracket Face8），全部自由度固定 | ux=uy=uz=0 |
| 载荷 | 立板顶面 z=88（Bracket Face4） | 合计 **500 N**，方向 **−X** |

- FreeCAD 的力载荷按面自动分配到 343 个节点（`*CLOAD`），合力 500 N；
- 方向用「一条平行 X 的边（Edge8）+ Reversed」定义，避免 GUI 直接输入向量报 `Invalid syntax`（见 §10 坑 2）。

## 6. 求解设置

- 求解器：CalculiX **2.22**（`F:\FreeCAD\bin\ccx.EXE`），spooles 对称求解器
- 线性静力、1 步；wall time ≈ 5 s
- 日志：`number of equations 95100`、`CalculiX done without error!`
- 工作目录：`03-计算\ccx\Unnamed\SolverCcxTools`（项目内，便于归档）

## 7. 结果

| 指标 | FEA | 手算/理论 | 偏差 |
|---|---|---|---|
| 立板顶面 X 向最大挠度 | **−0.1525 mm**（合成 0.1530） | 0.1587 mm | −3.6% |
| 全场最大 von Mises | **61.68 MPa** | 62.5 MPa（根部弯曲理论） | −1.3% |
| 峰值位置 | 节点 4291，坐标 (8.12, 38.42, 14.61)，位于 **R8 圆角曲面** | 立板根部截面 | — |
| 立板根部 z=8~12 最大 | 52.7 MPa | — | — |
| 安全系数 | **SF = 235 / 61.68 = 3.81** | 判据 ≥2.0 | **通过** |

- 应力超过 45 MPa 的节点共 1 043 个，集中在圆角及其上方一段——应力沿圆角平滑过渡，无尖角集中；
- 孔边未成为控制部位；
- 云图：`04-结果\云图-应力-FreeCAD.png`、`04-结果\云图-位移-FreeCAD.png`（FreeCAD 后处理按 SI 显示：位移 m、应力 Pa，色标顶端 6.168e+07 = 61.68 MPa）。

## 8. 手算对比

把立板视为根部（z=8）完全固定的悬臂，长度 L=80 mm，截面 60×8：

- 惯性矩：I = 60×8³/12 = 2 560 mm⁴
- 端部挠度：δ = FL³/(3EI) = 500×80³/(3×210000×2560) = **0.1587 mm**
- 根部弯曲应力：σ = M·c/I = (500×80)×4/2560 = **62.5 MPa**

FEA 挠度比手算小 3.6%：手算把立板根部当作理想固支；实际结构里底座板和 R8 圆角参与传力，根部更"刚"，因此挠度偏小、峰值应力也略低（−1.3%），趋势合理。

## 9. 结论

1. 在 500 N 侧向载荷下，最大 von Mises 应力 61.7 MPa，**安全系数 3.8**，满足 SF ≥ 2 的判据；
2. 自由端位移 0.153 mm，刚度充裕；
3. R8 圆角有效消除了内角应力集中（尖角时 Kt≈1.5~2，峰值会升至 90~120 MPa）；
4. 本算例为线弹性、单向静载；若实际为交变载荷，应补充疲劳评定（可用 `tools\疲劳\fatigue.py` 配 S-N 曲线）。

## 10. 复现步骤（要点）

1. 建模：Part 工作台两个 Box → 布尔并集 → R8 圆角 → 4×Ø9 孔；
2. 复制 ASCII 名几何参与网格：`b=addObject('Part::Feature','Bracket'); b.Shape=s`；
3. FEM：分析容器 → 材料（Python 直接写字典）：

   ```python
   o = App.ActiveDocument.MaterialSolid
   mat = o.Material
   mat.update({'Name': 'CalculiX-Steel', 'YoungsModulus': '210000 MPa',
               'PoissonRatio': '0.3', 'Density': '7900 kg/m^3'})
   o.Material = mat
   ```

4. Gmsh 网格：2 阶、3.0/0.5 mm；
5. 约束/载荷（Python）：

   ```python
   import ObjectsFem
   ana = App.ActiveDocument.Analysis; b = App.ActiveDocument.Bracket
   fix = ObjectsFem.makeConstraintFixed(App.ActiveDocument, 'Fixed-Bottom')
   fix.References = [(b, 'Face8')]; ana.addObject(fix)
   cf = ObjectsFem.makeConstraintForce(App.ActiveDocument, 'Force-Top')
   cf.References = [(b, 'Face4')]
   cf.Force = '500 N'          # 必须带单位！数字=内部单位 kg·mm/s²=mN
   cf.Direction = (b, ['Edge8']); cf.Reversed = True
   ana.addObject(cf)
   ```

6. 求解器偏好（避免 ccx 找不到、结果落临时目录）：

   ```python
   import FreeCAD
   g = FreeCAD.ParamGet('User parameter:BaseApp/Preferences/Mod/Fem/General')
   g.SetBool('UseBesideDirectory', False); g.SetBool('UseTempDirectory', False)
   g.SetBool('UseCustomDirectory', True)
   g.SetString('CustomDirectoryPath', r'D:\E\项目\项目\002-L形支架静力分析\03-计算\ccx')
   FreeCAD.ParamGet('User parameter:BaseApp/Preferences/Mod/Fem/Ccx').SetString('ccxBinaryPath', r'F:\FreeCAD\bin\ccx.EXE')
   ```

7. 后处理：`F:\Python3.13.13\python.exe 03-计算\postprocess_bracket.py`

### 本算例踩过的坑

1. **Gmsh 不支持中文路径**：FreeCAD 传 UTF-8 路径，Windows Gmsh 按 ANSI 解析 → `Unable to open file 'D:/E/ÏîÄ¿/...'`。对象内部 Name 只读无法改，解决：建 ASCII 名 Part::Feature 副本，或用 ASCII 临时目录。
2. **力方向不能用向量**：Direction 是 PropertyLinkSub，必须指向一条边 + Reversed。
3. **Python 赋 Force 要带单位**：`cf.Force = 500` 表示 500 mN（内部单位 kg·mm/s²），结果小 1000 倍；应写 `'500 N'`。
4. **求解工作目录默认在系统临时目录**，需在偏好里改为项目 `03-计算`。
5. 对象内部 Name ≠ Label（`Force_Top` vs `Force_Top`/显示名），`getObject` 用内部名。

## 11. 文件清单

| 路径 | 内容 |
|---|---|
| `01-几何\L形支架.FCStd` | 几何 + FEM 设置（材料/网格/约束/载荷/求解器） |
| `03-计算\postprocess_bracket.py` | .frd 解析 → 挠度/应力/安全系数 |
| `03-计算\bracket_summary.txt` | 关键结果摘要 |
| `03-计算\bracket_topnodes.csv` | 应力前 30 节点 |
| `03-计算\ccx\Unnamed\SolverCcxTools\` | inp/frd/dat/sta/cvg 原始求解文件 |
| `04-结果\` | frd、摘要、CSV、FreeCAD 云图截图 |
| `05-报告\计算书-L形支架静力校核.md` | 本文件 |

## 12. 变更记录

| 日期 | 变更 | 说明 |
|---|---|---|
| 2026-11-12 | 初版 | 建模→网格→求解→后处理→对比手算 |
| 2026-11-12 | 修正载荷 | Python 直接赋 500 得到 0.5 N，改为 `'500 N'` 后重算 |
