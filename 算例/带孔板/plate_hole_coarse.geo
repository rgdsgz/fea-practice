// 粗网格版本（全局 3.0 mm，不做孔边加密）——用于网格收敛性对比
SetFactory("OpenCASCADE");
Box(1) = {0, 0, 0, 100, 50, 5};
Cylinder(2) = {50, 25, 0, 0, 0, 10, 5};
BooleanDifference(3) = { Volume{1}; Delete; } { Volume{2}; Delete; };
Mesh.CharacteristicLengthMin = 3.0;
Mesh.CharacteristicLengthMax = 3.0;
Mesh.Algorithm3D = 1;
