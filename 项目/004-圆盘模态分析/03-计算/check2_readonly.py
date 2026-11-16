# -*- coding: utf-8 -*-
# 004 只读自检：核对材料密度/约束/求解器（不保存）
import FreeCAD as App

P = r"D:\E\Model\项目\004-圆盘模态分析\01-几何\Disc.FCStd"
doc = App.openDocument(P)
L = []
L.append("=" * 62)
for o in doc.Objects:
    L.append("OBJ %-22s %-24s label=%s" % (o.Name, o.TypeId, o.Label))
L.append("-" * 62)

mat = doc.getObject("MaterialSolid")
if mat is None:
    L.append("!! MaterialSolid NOT FOUND")
else:
    L.append("MATERIAL category = " + str(mat.Category))
    keys = list(mat.Material.keys())
    for k in sorted(keys):
        L.append("   %-30s = %s" % (k, mat.Material[k]))
    L.append("-" * 40)
    for k in ("YoungsModulus", "PoissonRatio", "Density"):
        L.append("   %-14s present=%s  value=%r" % (k, k in keys, mat.Material.get(k)))
    try:
        d = mat.Material["Density"]
        q = App.Units.Quantity(d)
        L.append("   -> t/mm^3 = %.6e" % q.getValueAs("t/mm^3").Value)
    except Exception as e:
        L.append("   !! Density error: %r" % (e,))

L.append("-" * 62)
fx = doc.getObject("ConstraintFixed")
d = doc.getObject("Disc")
if fx is None:
    L.append("!! ConstraintFixed NOT FOUND")
else:
    L.append("FIXED references = %r" % (fx.References,))
    try:
        for (obj, subs) in fx.References:
            for s in subs:
                i = int(str(s).replace("Face", "")) - 1
                L.append("   %s -> area = %.3f mm2" % (s, d.Shape.Faces[i].Area))
    except Exception as e:
        L.append("   !! face check error: %r" % (e,))

L.append("-" * 62)
sv = doc.getObject("SolverCcxTools")
if sv is None:
    L.append("!! SolverCcxTools NOT FOUND")
else:
    for k in ("AnalysisType", "EigenmodesCount", "EigenmodeLowLimit",
              "EigenmodeHighLimit", "GeometricalNonlinearity", "MatrixSolverType"):
        try:
            L.append("   %-20s = %s" % (k, getattr(sv, k)))
        except Exception as e:
            L.append("   %-20s ! %r" % (k, e))
L.append("=" * 62)

with open(r"D:\E\Model\项目\004-圆盘模态分析\03-计算\check2_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("written")
