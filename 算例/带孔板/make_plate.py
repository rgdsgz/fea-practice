"""用 FreeCAD 无界面生成「带中心圆孔的拉伸板」并导出 STEP。

几何：100 mm (X) × 50 mm (Y) × 5 mm (Z)，中心 Ø10 圆孔（孔心 x=50, y=25）
用途：FEA 应力集中系数 Kt 验证算例。

用法：
    F:\\FreeCAD\\bin\\freecadcmd.exe "D:\\E\\项目\\算例\\带孔板\\make_plate.py"
"""
import os

import FreeCAD
import Part
from FreeCAD import Vector

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT_DIR, exist_ok=True)

LENGTH = 100.0   # X
WIDTH = 50.0     # Y
THICK = 5.0      # Z
HOLE_D = 10.0    # 中心孔直径

box = Part.makeBox(LENGTH, WIDTH, THICK)
hole = Part.makeCylinder(HOLE_D / 2.0, THICK, Vector(LENGTH / 2, WIDTH / 2, 0))
shape = box.cut(hole)

step_path = os.path.join(OUT_DIR, "plate_hole_100x50x5.stp")
Part.export([shape], step_path)

# 另存一份 FCStd 方便在 FreeCAD 里直接改参数
doc = FreeCAD.newDocument("PlateWithHole")
obj = doc.addObject("Part::Feature", "PlateWithHole")
obj.Shape = shape
doc.recompute()
fcstd = os.path.join(OUT_DIR, "plate_hole_100x50x5.FCStd")
doc.saveAs(fcstd)

bb = shape.BoundBox
print(f"[OK] 体积 = {shape.Volume:.1f} mm^3（理论 {(LENGTH*WIDTH - 3.1415926*HOLE_D**2/4)*THICK:.1f}）")
print(f"[OK] 尺寸 = {bb.XLength:.1f} × {bb.YLength:.1f} × {bb.ZLength:.1f} mm")
print(f"[OK] STEP  = {step_path}")
print(f"[OK] FCStd = {fcstd}")
