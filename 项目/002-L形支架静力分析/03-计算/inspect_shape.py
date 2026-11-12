import FreeCAD, Part
doc = FreeCAD.openDocument(r"D:\E\项目\项目\002-L形支架静力分析\01-几何\L形支架.FCStd")
for o in doc.Objects:
    print(o.Name, '|', o.Label, '|', o.TypeId)
o = doc.getObject('带孔支架')
s = o.Shape
print('valid=', s.isValid(), 'volume=', s.Volume, 'solids=', len(s.Solids), 'shells=', len(s.Shells), 'faces=', len(s.Faces), 'edges=', len(s.Edges))
print('type=', s.ShapeType)
p = r"D:\E\项目\项目\002-L形支架静力分析\02-网格\bracket.brep"
s.exportBrep(p)
print('brep exported')
