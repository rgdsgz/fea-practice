# -*- coding: utf-8 -*-
# 004 圆盘模态分析 —— 步骤 1：建模 + 自检
# 用法（FreeCAD Python 控制台粘贴一行）：
#   exec(open(r'D:\E\Model\项目\004-圆盘模态分析\03-计算\step1_build.py',encoding='utf-8').read())
import os
import math
import FreeCAD as App

R = 100.0   # 半径 mm
T = 6.0     # 厚度 mm
OUT = os.environ.get("D004_OUT",
                     r"D:\E\Model\项目\004-圆盘模态分析\01-几何\Disc.FCStd")

# 清理同名文档，保证可重复执行
for _n in list(App.listDocuments().keys()):
    if _n == "DiscModal":
        App.closeDocument(_n)

doc = App.newDocument("DiscModal")
disc = doc.addObject("Part::Cylinder", "Disc")   # 内部 Name 直接就是 ASCII
disc.Label = "Disc"
disc.Radius = R
disc.Height = T
disc.Angle = 360.0
disc.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())
doc.recompute()

s = disc.Shape
bb = s.BoundBox
print("-" * 62)
print("[1] OBJECT")
print("    internal Name :", disc.Name)
print("    Label         :", disc.Label)
print("    TypeId        :", disc.TypeId)
print("[2] SHAPE CHECK")
print("    isValid       :", s.isValid())
print("    Volume  [mm3] : %12.3f   theory %12.3f" % (s.Volume, math.pi * R * R * T))
print("    Area    [mm2] : %12.3f   theory %12.3f"
      % (s.Area, 2 * math.pi * R * R + 2 * math.pi * R * T))
print("    BBox X        : %8.3f .. %8.3f" % (bb.XMin, bb.XMax))
print("    BBox Y        : %8.3f .. %8.3f" % (bb.YMin, bb.YMax))
print("    BBox Z        : %8.3f .. %8.3f" % (bb.ZMin, bb.ZMax))
print("    Solids/Shells : %d / %d" % (len(s.Solids), len(s.Shells)))
print("[3] FACES  (need the cylindrical side face for the fixed BC)")
print("    idx   Area[mm2]    center (x, y, z)            normal")
for i, f in enumerate(s.Faces):
    c = f.CenterOfMass
    try:
        n = f.normalAt(0.5, 0.5)
        ns = "(%+.3f,%+.3f,%+.3f)" % (n.x, n.y, n.z)
    except Exception:
        ns = "(n/a)"
    print("    %-4d %11.3f  (%8.3f,%8.3f,%8.3f)  %s"
          % (i + 1, f.Area, c.x, c.y, c.z, ns))
side = [i + 1 for i, f in enumerate(s.Faces) if abs(f.Area - 2 * math.pi * R * T) < 1.0]
print("    -> cylindrical side face index =", side)
print("[4] SAVE")
doc.saveAs(OUT)
print("    path   :", OUT)
print("    exists :", os.path.exists(OUT))
if os.path.exists(OUT):
    print("    size   : %d bytes" % os.path.getsize(OUT))
print("-" * 62)
