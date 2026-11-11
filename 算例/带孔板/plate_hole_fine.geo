// 细网格版本（孔边 0.4 mm）——用于网格收敛性对比
SetFactory("OpenCASCADE");
Box(1) = {0, 0, 0, 100, 50, 5};
Cylinder(2) = {50, 25, 0, 0, 0, 10, 5};
BooleanDifference(3) = { Volume{1}; Delete; } { Volume{2}; Delete; };
Field[1] = Distance;
Field[1].SurfacesList = {2};
Field[2] = Threshold;
Field[2].InField = 1;
Field[2].SizeMin = 0.4;
Field[2].SizeMax = 2.5;
Field[2].DistMin = 0.5;
Field[2].DistMax = 10.0;
Background Field = 2;
Mesh.CharacteristicLengthMin = 0.3;
Mesh.CharacteristicLengthMax = 2.5;
Mesh.Algorithm3D = 1;
