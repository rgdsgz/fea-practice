// 带中心圆孔拉伸板：100 x 50 x 5 mm，中心 Ø10 孔
// 用法：gmsh plate.geo -0 -format stp -o plate_hole.stp
//       或  gmsh plate.geo -3 -format inp -o plate_hole.inp
SetFactory("OpenCASCADE");

Box(1) = {0, 0, 0, 100, 50, 5};
Cylinder(2) = {50, 25, 0, 0, 0, 10, 5};
BooleanDifference(3) = { Volume{1}; Delete; } { Volume{2}; Delete; };

// 网格：整体 2.5 mm，孔边 0.6 mm（Distance + Threshold 尺寸场）
Field[1] = Distance;
Field[1].SurfacesList = {2};
Field[2] = Threshold;
Field[2].InField = 1;
Field[2].SizeMin = 0.6;
Field[2].SizeMax = 2.5;
Field[2].DistMin = 0.5;
Field[2].DistMax = 12.0;
Background Field = 2;

Mesh.CharacteristicLengthMin = 0.4;
Mesh.CharacteristicLengthMax = 2.5;
Mesh.Algorithm3D = 1; // Delaunay
