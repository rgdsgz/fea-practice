# -*- coding: utf-8 -*-
# 004 网格生成（headless 安全版）
# AGENTS.md §6 #19：FreeCAD 1.1 的 GmshTools 异步且命令行参数有 bug，
# 这里只用它的 prepare() 写 .geo，然后自己调 gmsh 命令行，最后 Fem.read 导回。
import os
import subprocess
import traceback
import FreeCAD as App
import ObjectsFem
import Fem

FCSTD = r"D:\E\Model\项目\004-圆盘模态分析\01-几何\Disc.FCStd"
PROJDIR = r"D:\E\Model\项目\004-圆盘模态分析"
WORK = os.path.join(PROJDIR, r"03-计算\ccx")
GMSH = r"F:\FreeCAD\bin\gmsh.exe"
LOG = os.path.join(PROJDIR, r"03-计算\mesh_log.txt")

SIZE = os.environ.get("D004_SIZE", "4")
NAME = os.environ.get("D004_NAME", "FEMMesh4mm")

_logf = open(LOG, "w", encoding="utf-8")


def log(msg):
    _logf.write(str(msg) + "\n")
    _logf.flush()


try:
    os.makedirs(WORK, exist_ok=True)

    p = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/General")
    p.SetString("CustomDirectoryPath", WORK)
    p.SetBool("UseCustomDirectory", True)
    p.SetBool("UseTempDirectory", False)
    p.SetBool("UseBesideDirectory", False)
    log("[0] work dir -> " + WORK)

    doc = None
    for n, d in App.listDocuments().items():
        if d.FileName and os.path.normcase(d.FileName) == os.path.normcase(FCSTD):
            doc = d
            break
    if doc is None:
        doc = App.openDocument(FCSTD)
    log("[1] doc opened: " + str(doc.FileName))

    disc = doc.getObject("Disc")
    analysis = doc.getObject("Analysis")
    log("[2] disc=%r analysis=%r" % (disc, analysis))

    for o in list(doc.Objects):
        if o.TypeId == "Fem::FemMeshGmsh":
            doc.removeObject(o.Name)
    doc.recompute()
    log("[3] old meshes removed")

    mesh = ObjectsFem.makeMeshGmsh(doc, NAME)
    mesh.Label = NAME
    mesh.Shape = disc
    mesh.CharacteristicLengthMax = "%s mm" % SIZE
    mesh.CharacteristicLengthMin = "0.2 mm"
    mesh.ElementOrder = "2nd"
    analysis.addObject(mesh)
    doc.recompute()
    log("[4] mesh object created: " + mesh.Name)

    from femmesh.gmshtools import GmshTools
    gt = GmshTools(mesh)
    gt.prepare()
    geo = gt.temp_file_geo
    log("[5] prepared geo=" + geo)
    log("    exists=%s" % os.path.exists(geo))

    wd = os.path.dirname(geo)
    gn = os.path.basename(geo)
    unv_name = NAME + ".unv"
    unv = os.path.join(wd, unv_name)
    cmd = [GMSH, gn, "-3", "-format", "unv", "-o", unv_name, "-v", "3"]
    log("[6] " + " ".join(cmd))
    log("    cwd=" + wd)
    with open(os.path.join(wd, "gmsh_stdout.txt"), "w", encoding="utf-8", errors="replace") as fo:
        rc = subprocess.call(cmd, cwd=wd, stdout=fo, stderr=subprocess.STDOUT)
    log("[7] gmsh exit = %d" % rc)
    log("    unv exists=%s size=%s"
        % (os.path.exists(unv), os.path.getsize(unv) if os.path.exists(unv) else -1))

    if rc != 0 or not os.path.exists(unv):
        raise RuntimeError("gmsh failed")

    fmesh = Fem.read(unv)
    log("[8] Fem.read ok: nodes=%d volumes=%d" % (fmesh.NodeCount, len(fmesh.Volumes)))
    names = []
    for gid in fmesh.Groups:
        try:
            names.append(fmesh.getGroupName(gid))
        except Exception:
            names.append("g%d" % gid)
    log("    groups=" + ", ".join(sorted(names)))

    mesh.FemMesh = fmesh
    doc.recompute()
    log("[9] assigned: nodes=%d volumes=%d"
        % (mesh.FemMesh.NodeCount, len(mesh.FemMesh.Volumes)))

    doc.save()
    log("[10] saved " + str(doc.FileName))

except Exception:
    log("[!!] EXCEPTION\n" + traceback.format_exc())

finally:
    _logf.close()
