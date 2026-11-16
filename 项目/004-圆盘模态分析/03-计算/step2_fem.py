# -*- coding: utf-8 -*-
# 004 圆盘模态分析 —— 步骤 2：FEM 容器 + 材料（含密度）+ 侧面固定约束 + 频率求解器
# 用法（FreeCAD Python 控制台）：
#   exec(open(r'D:\E\Model\项目\004-圆盘模态分析\03-计算\step2_fem.py',encoding='utf-8').read())
import os
import FreeCAD as App
import ObjectsFem

FCSTD = r"D:\E\Model\项目\004-圆盘模态分析\01-几何\Disc.FCStd"

# ---------- 打开文档 ----------
doc = None
for n, d in App.listDocuments().items():
    if d.FileName and os.path.normcase(d.FileName) == os.path.normcase(FCSTD):
        doc = d
        break
if doc is None:
    doc = App.openDocument(FCSTD)

disc = doc.getObject("Disc")
assert disc is not None, "找不到对象 Disc，先跑 step1_build.py"
assert len(disc.Shape.Faces) == 3, "面数不是 3，几何不对"

# ---------- 清理旧的分析（可重复执行） ----------
for o in list(doc.Objects):
    if o.TypeId.startswith("Fem::") or o.TypeId in ("Fem::FemAnalysis",):
        doc.removeObject(o.Name)
doc.recompute()

# ---------- 1. 分析容器 ----------
analysis = ObjectsFem.makeAnalysis(doc, "Analysis")
analysis.Label = "Modal"

# ---------- 2. 材料（必须有密度！） ----------
mat = ObjectsFem.makeMaterialSolid(doc, "MaterialSolid")
mat.Label = "Steel"
mat.Category = "Solid"
mat.Material = {
    "Name": "CalculiX-Steel",
    "YoungsModulus": "210000 MPa",
    "PoissonRatio": "0.30",
    "Density": "7900 kg/m^3",          # = 7.9e-9 t/mm^3
}
analysis.addObject(mat)                # 坑：不 addObject 就不在分析里

# ---------- 3. 固定约束：圆柱侧面 ----------
# 侧面 = 面积最小的那个面（3769.911 mm²）；step1 已确认是 Face1
side_idx = min(range(len(disc.Shape.Faces)),
               key=lambda i: disc.Shape.Faces[i].Area) + 1
fixed = ObjectsFem.makeConstraintFixed(doc, "Fixed")
fixed.Label = "Fixed-Side"
fixed.References = [(disc, "Face%d" % side_idx)]
analysis.addObject(fixed)

# ---------- 4. 求解器：频率分析 ----------
solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "SolverCcxTools")
solver.Label = "Frequency"
solver.AnalysisType = "frequency"
solver.EigenmodesCount = 12          # 取前 12 阶（理论前 13 阶到 13275 Hz）
solver.EigenmodeLowLimit = "0 Hz"
solver.EigenmodeHighLimit = "0 Hz"   # 0,0 = 不限频率范围，只按阶数
solver.GeometricalNonlinearity = "linear"
analysis.addObject(solver)

doc.recompute()

# ---------- 自检 ----------
print("-" * 62)
print("[1] ANALYSIS")
print("    name    :", analysis.Name, "/", analysis.Label)
print("    members :", [o.Name for o in analysis.Group])
print("[2] MATERIAL")
print("    category:", mat.Category)
for k in ("Name", "YoungsModulus", "PoissonRatio", "Density"):
    print("    %-12s: %s" % (k, mat.Material.get(k, "<MISSING>")))
try:
    q = App.Units.Quantity(mat.Material["Density"])
    print("    -> in t/mm^3 : %.6e" % q.getValueAs("t/mm^3").Value)
except Exception as e:
    print("    !! density parse error:", e)
print("[3] CONSTRAINT")
print("    face    : Face%d  area = %.3f mm2" % (side_idx, disc.Shape.Faces[side_idx - 1].Area))
print("    refs    :", fixed.References)
print("[4] SOLVER")
print("    type    :", solver.AnalysisType)
print("    modes   :", solver.EigenmodesCount)
print("    freqs   : low=%s high=%s" % (solver.EigenmodeLowLimit, solver.EigenmodeHighLimit))
print("[5] SAVE")
doc.save()
print("    saved   :", doc.FileName)
print("-" * 62)
