"""带孔板 Kt 验证：Gmsh 网格 → 组装 CalculiX 输入 → 求解 → 提取最大 von Mises。

用法（用系统 Python，含 numpy）：
    F:\\Python3.13.13\\python.exe "D:\\E\\项目\\算例\\带孔板\\run_kt.py"

理论值（d/W=10/50=0.2，净截面 Kt ≈ 2.508，见 Peterson）：
    σ_gross = 100 MPa, σ_net = 125 MPa, σ_max ≈ 313.5 MPa
"""
import csv
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))  # D:\E\项目
FATIGUE_DIR = os.path.join(TOOLS, "tools", "疲劳")
sys.path.insert(0, FATIGUE_DIR)

import numpy as np

from frd_stress import parse_frd_stress

GEO_INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "plate_hole_l2.inp")
CCX_CANDIDATES = [
    os.path.join(TOOLS, "tools", "PrePoMax", "Solver", "ccx_dynamic.exe"),
    r"F:\FreeCAD\bin\ccx.exe",
]
LENGTH, WIDTH, THICK, HOLE_D = 100.0, 50.0, 5.0, 10.0
SIGMA_GROSS = 100.0  # MPa
E, NU = 210000.0, 0.3
JOB = sys.argv[2] if len(sys.argv) > 2 else "plate_hole_ccx"
BC_MODE = os.environ.get("KT_BC", "all")  # all = 左端面全约束；minimal = 只约束 x + 单点 y/z


def parse_gmsh_inp(path):
    nodes = {}
    elements = []
    mode = None
    etype = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("*"):
                low = s.lower()
                if low.startswith("*node"):
                    mode = "node"
                elif low.startswith("*element"):
                    mode = "elem"
                    if "type=" in low:
                        etype = low.split("type=")[1].split(",")[0].strip()
                else:
                    mode = None
                continue
            parts = [p.strip() for p in s.split(",")]
            if mode == "node" and len(parts) >= 4:
                nodes[int(parts[0])] = (float(parts[1]), float(parts[2]), float(parts[3]))
            elif mode == "elem" and etype in ("c3d4", "c3d10"):
                elements.append([int(p) for p in parts])
    return nodes, elements


def vm(t):
    sxx, syy, szz, sxy, syz, szx = t
    return math.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2)
    )


def build_deck(nodes, elements, path):
    nfix = sorted(n for n, (x, y, z) in nodes.items() if x <= 1e-6)
    # C3D10 面定义（Abaqus/CalculiX）：面号 -> 角节点局部索引（0 基）
    FACE_DEFS = {1: (0, 1, 2), 2: (0, 3, 1), 3: (1, 3, 2), 4: (2, 3, 0)}
    face_loads = []
    for i, conn in enumerate(elements, start=1):
        corners = conn[1:5]
        coords = [nodes[n] for n in corners]
        for fid, idx in FACE_DEFS.items():
            pts = [coords[j] for j in idx]
            if all(abs(p[0] - LENGTH) < 1e-6 for p in pts):
                face_loads.append((i, fid))
                break

    with open(path, "w", encoding="utf-8") as f:
        f.write("*HEADING\nplate with hole - Kt validation\n")
        f.write("*NODE\n")
        for nid, (x, y, z) in sorted(nodes.items()):
            f.write(f"{nid}, {x:.6g}, {y:.6g}, {z:.6g}\n")
        enodes = len(elements[0]) - 1
        etype = "C3D10" if enodes == 10 else "C3D4"
        f.write(f"*ELEMENT, TYPE={etype}, ELSET=Eall\n")
        for i, conn in enumerate(elements, start=1):
            f.write(f"{i}, " + ", ".join(str(n) for n in conn[1:]) + "\n")
        f.write("*NSET, NSET=Nfix\n")
        for i in range(0, len(nfix), 16):
            f.write(", ".join(str(n) for n in nfix[i:i + 16]) + "\n")
        f.write("*MATERIAL, NAME=STEEL\n*ELASTIC\n")
        f.write(f"{E:.6g}, {NU}\n")
        f.write("*SOLID SECTION, ELSET=Eall, MATERIAL=STEEL\n1.0\n")
        if BC_MODE == "minimal":
            # 仅约束左端面 x 向位移，再各取一个节点约束 y、z，避免端部泊松约束带来的附加应力
            left = [(n,) + nodes[n] for n in nfix]
            ymax = max(left, key=lambda r: r[2])[0]
            zmax = max(left, key=lambda r: r[3])[0]
            f.write(f"*NSET, NSET=Nyz\n{ymax}, {zmax}\n")
            f.write("*BOUNDARY\nNfix, 1, 1, 0.0\n")
            f.write(f"{ymax}, 2, 2, 0.0\n{zmax}, 3, 3, 0.0\n")
        else:
            f.write("*BOUNDARY\nNfix, 1, 3, 0.0\n")
        f.write("*STEP\n*STATIC\n")
        # 面压力：正 P 为压向面内，这里要拉伸（+X 方向），取负值
        f.write("*DLOAD\n")
        for eid, fid in face_loads:
            f.write(f"{eid}, P{fid}, {-SIGMA_GROSS:.6g}\n")
        f.write("*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n")
    print(f"[deck] {path}: {len(nodes)} 节点, {len(elements)} 单元, "
          f"固定 {len(nfix)} 节点, 压力面 {len(face_loads)} 个单元面")


def main():
    if not os.path.exists(GEO_INP):
        raise SystemExit(f"找不到网格文件 {GEO_INP}，先运行 gmsh -3 -order 2 -format inp")
    nodes, elements = parse_gmsh_inp(GEO_INP)
    print(f"[mesh] {len(nodes)} 节点, {len(elements)} 个 C3D4/C3D10 单元")
    deck = os.path.join(HERE, JOB + ".inp")
    build_deck(nodes, elements, deck)

    ccx = next((p for p in CCX_CANDIDATES if os.path.exists(p)), None)
    if not ccx:
        raise SystemExit("没找到 CalculiX 可执行文件")
    print(f"[solve] {ccx} -i {JOB}")
    proc = subprocess.run([ccx, "-i", JOB], cwd=HERE, capture_output=True, text=True,
                          errors="replace")
    tail = [ln for ln in proc.stdout.splitlines() if "Job finished" in ln or "ERROR" in ln]
    print("[ccx]", tail or "no summary", "exit=", proc.returncode)

    frd = os.path.join(HERE, JOB + ".frd")
    data = parse_frd_stress(frd)
    print(f"[result] {len(data)} 个节点应力")

    rows = []
    for nid, t in data.items():
        x, y, z = nodes.get(nid, (float("nan"),) * 3)
        rows.append((nid, x, y, z, vm(t)))
    rows.sort(key=lambda r: -r[4])
    max_row = rows[0]
    near_hole = [r for r in rows if 40.0 < r[1] < 60.0]
    max_hole = near_hole[0] if near_hole else max_row
    sxx_avg = float(np.mean([t[0] for t in data.values()]))

    sig_net = SIGMA_GROSS / (1 - HOLE_D / WIDTH)
    kt_net = 3 - 3.13 * (HOLE_D / WIDTH) + 3.66 * (HOLE_D / WIDTH) ** 2 - 1.53 * (HOLE_D / WIDTH) ** 3
    sig_max_theory = kt_net * sig_net
    print(f"\n===== Kt 验证 =====")
    print(f"平均 SXX = {sxx_avg:.1f} MPa（应为正，说明确实在拉伸）")
    print(f"毛截面应力 σ_gross      = {SIGMA_GROSS:.1f} MPa")
    print(f"净截面应力 σ_net        = {sig_net:.1f} MPa")
    print(f"Peterson 净截面 Kt      = {kt_net:.3f}")
    print(f"理论最大应力 σ_max      = {sig_max_theory:.1f} MPa")
    print(f"FEA 孔边最大 von Mises  = {max_hole[4]:.1f} MPa  (node {max_hole[0]}, "
          f"x={max_hole[1]:.2f}, y={max_hole[2]:.2f})")
    print(f"等效 Kt (相对净截面)    = {max_hole[4] / sig_net:.3f}")
    print(f"与理论误差              = {(max_hole[4] - sig_max_theory) / sig_max_theory * 100:+.1f}%")
    print(f"全模型最大 von Mises    = {max_row[4]:.1f} MPa  (node {max_row[0]}, "
          f"x={max_row[1]:.2f}, y={max_row[2]:.2f})")

    out = os.path.join(HERE, "kt_results.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node", "x", "y", "z", "von_mises_MPa"])
        w.writerows(rows[:20])
    print(f"[OK] 前 20 个高应力节点 -> {out}")


if __name__ == "__main__":
    main()
