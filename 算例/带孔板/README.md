# 算例 01：带孔板拉伸 —— 应力集中系数 Kt 验证

> 目的：用**理论解已知**的算例验证整条链路（几何 → 网格 → CalculiX 求解 → 应力提取 → 理论对比）是否正确。
> 状态：✅ 已验证通过（2026-11-11）

## 1. 几何与工况

| 项目 | 数值 |
|---|---|
| 板尺寸 | 100 × 50 × 5 mm（X × Y × Z） |
| 中心圆孔 | Ø10 mm（孔心 x=50, y=25） |
| 材料 | 钢，E = 210000 MPa，ν = 0.3（线弹性） |
| 边界 | 左端面（x=0）固定 |
| 载荷 | 右端面（x=100）均布拉伸 100 MPa |
| 网格 | C3D10 二次四面体，孔边 0.4–0.6 mm，远处 2.5 mm |

## 2. 理论值（Peterson，净截面）

```
d/W = 10/50 = 0.2
Kt_net = 3 - 3.13(d/W) + 3.66(d/W)^2 - 1.53(d/W)^3 = 2.508
σ_net  = 100 / (1 - 0.2) = 125 MPa
σ_max  = Kt_net × σ_net = 313.5 MPa
```

## 3. FEA 结果与网格收敛性

| 网格 | 单元数 | 孔边最大 von Mises | 等效 Kt（净截面） | 与理论误差 |
|---|---|---|---|---|
| 粗（全局 3 mm） | 5,816 | 303.6 MPa | 2.429 | −3.2% |
| 中（孔边 0.6 mm） | 35,876 | 301.9 MPa | 2.415 | −3.7% |
| 细（孔边 0.4 mm） | 54,711 | 304.6 MPa | 2.436 | −2.9% |

三种网格结果稳定在 **Kt ≈ 2.42–2.44**，与理论 2.508 相差 **−3% 左右**（3D 板厚效应 + 端部约束 + 节点应力外推的综合影响，属正常范围）。

**结论：链路正确，应力结果可信（误差 <5%）；网格加密不再显著改变结果 → 已收敛。**

## 4. 文件说明

| 文件 | 用途 |
|---|---|
| `plate_hole.geo` | Gmsh 几何 + 网格脚本（含孔边加密） |
| `plate_hole.stp` | 几何 STEP（可导入 FreeCAD / PrePoMax） |
| `plate_hole_l2.inp` | Gmsh 生成的二阶四面体网格（Abaqus/CalculiX 格式） |
| `run_kt.py` | 一键：组装 CalculiX 输入 → 求解 → 提取应力 → 对比理论 |
| `plate_hole_ccx.inp` | 组装好的 CalculiX 输入文件 |
| `plate_hole_ccx.frd` | 结果文件 |
| `kt_results.csv` | 前 20 个高应力节点 |
| `kt_coarse / kt_medium / kt_fine` | 收敛性对比用的算例 |

## 5. 一键复现

```powershell
# 1) 生成网格（二阶）
F:\FreeCAD\bin\gmsh.exe plate_hole.geo -3 -order 2 -format inp -o plate_hole_l2.inp

# 2) 求解 + 对比
F:\Python3.13.13\python.exe run_kt.py

# 可选：只约束 x 向、单点 y/z（更接近纯拉伸）
$env:KT_BC='minimal'; F:\Python3.13.13\python.exe run_kt.py
```

## 6. 在 PrePoMax GUI 里复现（练习用）

1. **File → Import** 选 `plate_hole.stp`（单位 mm）
2. **Materials** 新建钢：E=210000 MPa，ν=0.3
3. **Constraints**：左端面（x=0）Fixed（U1=U2=U3=0）
4. **Loads**：右端面（x=100）Pressure = **−100 MPa**（负值表示拉离表面；PrePoMax 里按界面提示）
5. **Mesh**：全局 2 mm，孔边 0.5 mm；单元类型二阶四面体
6. **Run**，后处理看 von Mises 最大值（应在 300 MPa 左右，位置在孔边 y≈20 / y≈30）

## 7. 踩过的坑（重要）

1. **CalculiX 面压力必须用 `P1`~`P6` 标签**（如 `191, P1, -100.`）；只写 `P` 会让 ccx 直接崩溃（0xC0000005），不报错。
2. **节点力（\*CLOAD）不能均匀施加拉伸**：会在加载面四角产生虚假应力集中（本算例最大点会跑到 x=100 的角上，525 MPa）。
3. **FreeCAD 无界面 `Part.export` 导 STEP 会崩溃**（本机 1.1.4 + 命令行环境），改用 Gmsh OCC 生成几何；GUI 里导出正常。
4. Gmsh 布尔运算语法要写 `BooleanDifference(3) = {...}`（带等号），Cylinder 用 `{x,y,z,dx,dy,dz,r}` 七个参数（第 8 个是角度，不是高度）。
