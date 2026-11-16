# -*- coding: utf-8 -*-
"""004 圆盘模态分析：三档网格自动收敛分析

流程（完全不依赖 FreeCAD GUI，可在系统 Python 下跑）：
  1. 复制 Shape2Mesh 的 .brep / .geo 到纯 ASCII 工作目录（gmsh 不支持中文路径）
  2. 改写 geo 里的 Mesh.CharacteristicLengthMax，gmsh -3 -format inp 导出
  3. 把 gmsh 的 inp 转成 CalculiX 输入卡：只留 C3D10 体单元，去掉 T3D3/CPS6 低维单元，
     补 *MATERIAL / *ELASTIC / *DENSITY / *SOLID SECTION / *STEP / *FREQUENCY / *BOUNDARY
  4. 跑 ccx_dynamic.exe，解析 .dat 的 EIGENVALUE OUTPUT

用法：python mesh_conv.py [档位 mm ...]   默认 4 3 2
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = r"D:\E\Model"
SRC = os.path.join(ROOT, r"fem004\Disc\FEMMeshGmsh")
WORKBASE = os.path.join(ROOT, "fem004", "mesh")      # 纯 ASCII
GMSH = r"F:\FreeCAD\bin\gmsh.exe"
CCX = os.path.join(ROOT, r"tools\PrePoMax\Solver\ccx_dynamic.exe")

R, T = 100.0, 6.0
MATERIAL = "MaterialSolid"


# ---------------------------------------------------------------- gmsh 阶段
def make_geo(h, work):
    """复制 brep/geo 并按档位改尺寸，返回 geo 路径"""
    os.makedirs(work, exist_ok=True)
    shutil.copy(os.path.join(SRC, "Disc_Geometry.brep"), work)
    with open(os.path.join(SRC, "shape2mesh.geo"), encoding="utf-8") as fh:
        geo = fh.read()
    geo = re.sub(r"Mesh\.CharacteristicLengthMax\s*=\s*[\d.]+;",
                 "Mesh.CharacteristicLengthMax = %r;" % float(h), geo)
    geo = re.sub(r"Mesh\.CharacteristicLengthMin\s*=\s*[\d.]+;",
                 "Mesh.CharacteristicLengthMin = 0.2;", geo)
    geo = geo.replace('Save "Disc_Mesh.unv";', 'Save "disc.unv";')
    gp = os.path.join(work, "disc.geo")
    with open(gp, "w", encoding="utf-8") as fh:
        fh.write(geo)
    return gp


def run_gmsh(gp, work):
    out = os.path.join(work, "disc_raw.inp")
    if os.path.exists(out):
        os.remove(out)
    cmd = [GMSH, "disc.geo", "-3", "-format", "inp", "-o", "disc_raw.inp", "-v", "2"]
    p = subprocess.run(cmd, cwd=work, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if not os.path.exists(out):
        raise RuntimeError("gmsh failed: rc=%s\n%s\n%s" % (p.returncode, p.stdout[-2000:], p.stderr[-2000:]))
    return out


# ------------------------------------------------------- inp 解析 / 转换
def parse_gmsh_inp(path):
    """返回 (nodes{id:(x,y,z)}, elems[(id, [n1..n10])], elsets{name:[ids]}, nsets{name:[ids]})"""
    nodes = {}
    elems = []
    elsets = {}
    nsets = {}
    mode = None
    nset_name = None
    elset_name = None

    with open(path, "r", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            low = s.lower()
            if low.startswith("*node"):
                mode = "node"
                continue
            if low.startswith("*element"):
                mode = "elem"
                continue
            if low.startswith("*elset"):
                mode = "elset_data"
                m = re.search(r"elset=([^,]+)", s, re.I)
                elset_name = m.group(1) if m else "?"
                elsets.setdefault(elset_name, [])
                continue
            if low.startswith("*nset"):
                mode = "nset_data"
                m = re.search(r"nset=([^,]+)", s, re.I)
                nset_name = m.group(1) if m else "?"
                nsets.setdefault(nset_name, [])
                continue
            if s.startswith("*") or s.startswith("**"):
                mode = None
                continue

            if mode == "node":
                parts = s.split(",")
                nid = int(parts[0])
                nodes[nid] = (float(parts[1]), float(parts[2]), float(parts[3]))
            elif mode == "elem":
                parts = [p.strip() for p in s.split(",")]
                eid = int(parts[0])
                conn = [int(p) for p in parts[1:] if p]
                elems.append((eid, conn))
            elif mode == "elset_data":
                elsets[elset_name].extend(int(x) for x in s.split(",") if x.strip())
            elif mode == "nset_data":
                nsets[nset_name].extend(int(x) for x in s.split(",") if x.strip())
    return nodes, elems, elsets, nsets


def write_id_lines(fh, ids, per=10):
    """CalculiX 每行最多 16 个条目，超出报 *ERROR in splitline；按 10 个一行写。"""
    ids = list(ids)
    for i in range(0, len(ids), per):
        fh.write(", ".join(str(x) for x in ids[i:i + per]) + "\n")


def write_ccx(nodes, elems, fix_nodes, out, h):
    """写 CalculiX 模态输入卡"""
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("** 004 disc modal analysis, characteristic length %s mm\n" % h)
        fh.write("** written by mesh_conv.py\n")
        fh.write("*NODE, NSET=Nall\n")
        for nid in sorted(nodes):
            x, y, z = nodes[nid]
            fh.write("%d, %.10g, %.10g, %.10g\n" % (nid, x, y, z))

        fh.write("*ELEMENT, TYPE=C3D10, ELSET=Evolumes\n")
        for eid, conn in elems:
            fh.write("%d, %s\n" % (eid, ", ".join(str(c) for c in conn)))

        fh.write("*ELSET, ELSET=%sSolid\n" % MATERIAL)
        write_id_lines(fh, [eid for eid, _ in elems])

        fh.write("*NSET, NSET=ConstraintFixed\n")
        write_id_lines(fh, sorted(fix_nodes))

        fh.write("*MATERIAL, NAME=%s\n" % MATERIAL)
        fh.write("*ELASTIC\n210000, 0.3\n")
        fh.write("*DENSITY\n7.9E-09\n")
        fh.write("*SOLID SECTION, ELSET=%sSolid, MATERIAL=%s\n" % (MATERIAL, MATERIAL))
        fh.write("\n")
        fh.write("*STEP\n")
        fh.write("*FREQUENCY\n10, 0.0, 1000000.0\n")
        fh.write("*BOUNDARY\nConstraintFixed, 1\nConstraintFixed, 2\nConstraintFixed, 3\n")
        fh.write("*NODE FILE\nU\n")
        fh.write("*EL FILE\n")
        fh.write("*END STEP\n")


# --------------------------------------------------------------- ccx 阶段
def run_ccx(inp, work):
    base = os.path.splitext(os.path.basename(inp))[0]
    p = subprocess.run([CCX, base], cwd=work, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    dat = os.path.join(work, base + ".dat")
    frd = os.path.join(work, base + ".frd")
    if not os.path.exists(dat):
        raise RuntimeError("ccx failed: rc=%s\n%s\n%s" % (p.returncode, p.stdout[-3000:], p.stderr[-2000:]))
    return dat, frd, p.stdout


def parse_freqs(dat):
    """从 .dat 的 EIGENVALUE OUTPUT 表取 [(mode, cycles/time)]"""
    out = []
    in_tab = False
    with open(dat, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "EIGENVALUE" in line.replace(" ", "") and "OUTPUT" in line.replace(" ", ""):
                in_tab = True
                continue
            if in_tab:
                if "PARTICIPATION" in line.replace(" ", ""):
                    break
                m = re.match(r"^\s*(\d+)\s+([-\d.E+]+)\s+([-\d.E+]+)\s+([-\d.E+]+)", line)
                if m:
                    out.append((int(m.group(1)), float(m.group(4))))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    levels = sys.argv[1:] or ["4", "3", "2"]
    results = {}

    for h in levels:
        tag = "h%s" % h.replace(".", "p")
        work = os.path.join(WORKBASE, tag)
        print("\n" + "=" * 70)
        print("档位 %s mm  ->  %s" % (h, work))
        gp = make_geo(h, work)
        raw = run_gmsh(gp, work)
        nodes, elems, elsets, nsets = parse_gmsh_inp(raw)
        vols = [e for e in elems if len(e[1]) == 10]
        print("  gmsh: nodes=%d  全部单元=%d  C3D10=%d" % (len(nodes), len(elems), len(vols)))

        # 固定约束 = 圆柱侧面 Face1 的节点
        fix = sorted(set(nsets.get("Face1", [])))
        print("  固定约束节点（Face1 圆柱侧面）: %d" % len(fix))

        solve_inp = os.path.join(work, "disc_modal.inp")
        write_ccx(nodes, vols, fix, solve_inp, h)
        print("  写卡完成: %.1f MB" % (os.path.getsize(solve_inp) / 1e6))

        dat, frd, log = run_ccx(solve_inp, work)
        freqs = parse_freqs(dat)
        print("  ccx 前 6 阶（Hz）: " + ", ".join("%.2f" % f for _, f in freqs[:6]))
        results[h] = freqs

    # ---- 汇总 ----
    print("\n" + "=" * 78)
    print("三档网格收敛表（前 6 阶频率，Hz）")
    print("-" * 78)
    head = "%-6s" % "阶"
    for h in levels:
        head += "%-14s" % ("h=%smm" % h)
    head += "%-12s" % "极差"
    print(head)
    for i in range(6):
        row = "%-6d" % (i + 1)
        vals = []
        for h in levels:
            f = results[h][i][1] if i < len(results[h]) else float("nan")
            vals.append(f)
            row += "%-14.2f" % f
        spread = (max(vals) - min(vals)) / min(vals) * 100
        row += "%-12s" % ("%.2f%%" % spread)
        print(row)

    print("\n相对最细网格的偏差：")
    finest = levels[-1]
    for h in levels[:-1]:
        print("  h=%s mm:" % h, ", ".join(
            "%+.2f%%" % ((results[h][i][1] - results[finest][i][1]) / results[finest][i][1] * 100)
            for i in range(6)))


if __name__ == "__main__":
    main()
