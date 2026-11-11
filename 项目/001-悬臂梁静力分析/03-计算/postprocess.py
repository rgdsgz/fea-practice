# -*- coding: utf-8 -*-
"""悬臂梁算例后处理：解析 CalculiX .frd，提取位移/应力，与梁理论对比，出图出表。

算例：悬臂梁 100 x 10 x 10 mm，左端面 (x=0) 固定，右端面受 100 N 沿 -Z。
材料：CalculiX-Steel，E=210000 MPa，nu=0.3。
理论：δ_tip = F L^3 / (3 E I) = 0.190476 mm
      sigma(x) = F (L-x) * c / I，c = h/2 = 5 mm
      sigma(0) = 60 MPa，sigma(50) = 30 MPa

用法：F:\\FreeCAD\\bin\\python.exe 03-计算\\postprocess.py
输出：04-结果\\beam_results.csv（节点级）、04-结果\\beam_summary.txt、
      04-结果\\beam_displacement.png、04-结果\\beam_stress.png
"""
import csv
import math
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))          # 03-计算
PROJ = os.path.dirname(BASE)                                # 项目根
FRD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "FEMMeshGmsh.frd")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(PROJ, "04-结果")
os.makedirs(OUT, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJ, ".mplcache"))

# ---------- 算例参数（mm, N, MPa） ----------
L, b, h = 100.0, 10.0, 10.0
F, E = 100.0, 210000.0
I = b * h ** 3 / 12.0
c = h / 2.0
DELTA_THEORY = F * L ** 3 / (3.0 * E * I)
SIGMA_THEORY = lambda x: F * (L - x) * c / I
DELTA_CURVE = lambda x: F * x ** 2 * (3.0 * L - x) / (6.0 * E * I)


def parse_frd(path):
    """返回 (nodes, disp, stress)。nodes: id->(x,y,z)；disp/stress: id->[分量, ...]（最后一步）。"""
    nodes = {}
    disp = {}
    stress = {}
    mode = None
    cur = None
    name = None
    comps = 0

    def values(line, ncomp):
        # FRD 定宽：节点号占 3..13，之后每 12 字符一个 %12.5E；
        # 某些块 header 声明的分量数比实际数据多（如 DISP 声明 4 只有 3 个），按实际长度截断
        avail = (len(line.rstrip("\n")) - 13) // 12
        out = []
        for k in range(min(ncomp, avail)):
            out.append(float(line[13 + 12 * k:25 + 12 * k]))
        return out

    with open(path, "r", errors="replace") as f:
        for line in f:
            tag = line[:3].strip()
            kind = line[4:6] if len(line) > 5 else ""
            if kind == "2C":
                mode = "node"          # 节点块头：    2C
                continue
            if kind == "3C":
                mode = "elem"          # 单元块头：    3C
                continue
            if tag == "-4":
                parts = line.split()
                name = parts[1]
                comps = int(parts[2])
                mode = "res"
                cur = {}
            elif tag == "-3":
                if mode == "res" and cur is not None:
                    if name == "DISP":
                        disp = cur
                    elif name == "STRESS":
                        stress = cur        # 多步时保留最后一步
                mode = None
                cur = None
            elif tag == "-5":
                continue                    # 分量说明行（D1/SXX…），跳过
            elif tag == "-1":
                if "NODE" in line:
                    mode = "node"
                elif mode == "node":
                    nid = int(line[3:13])
                    nodes[nid] = tuple(values(line, 3))
                elif mode == "res":
                    nid = int(line[3:13])
                    cur[nid] = values(line, comps)
    return nodes, disp, stress


def von_mises(s):
    sxx, syy, szz, sxy, syz, szx = s
    return math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                     + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2))


def main():
    nodes, disp, stress = parse_frd(FRD)
    print(f"节点 {len(nodes)}，DISP 节点 {len(disp)}，STRESS 节点 {len(stress)}")
    if not nodes or not disp or not stress:
        sys.exit("FRD 解析不完整，检查文件格式")
    if set(disp) != set(nodes):
        print("警告：DISP 节点集合与 NODE 集合不一致")

    # 节点表：x,y,z,sxx..szx,vm,ux,uy,uz
    rows = []
    for nid, (x, y, z) in nodes.items():
        s = stress.get(nid)
        d = disp.get(nid)
        if not s or not d:
            continue
        vm = von_mises(s)
        rows.append((nid, x, y, z, *s, vm, *d))
    rows.sort(key=lambda r: r[0])
    csv_path = os.path.join(OUT, "beam_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["node", "x", "y", "z", "sxx", "syy", "szz", "sxy", "syz", "szx",
                    "von_mises", "ux", "uy", "uz"])
        w.writerows(rows)
    print(f"[OK] 节点结果 -> {csv_path}")

    tol = 1e-6
    # 1) 自由端挠度
    tip = [(r[0], r[13]) for r in rows if abs(r[1] - L) < tol]  # uz
    tip_uz = min(v for _, v in tip) if tip else float("nan")
    tip_abs = max(abs(v) for _, v in tip) if tip else float("nan")
    # 2) 跨中 x=50 上下表面
    mid_top = [r[10] for r in rows if abs(r[1] - L / 2) < tol and abs(r[3] - h) < tol]
    mid_bot = [r[10] for r in rows if abs(r[1] - L / 2) < tol and abs(r[3]) < tol]
    # 3) 固定端 x=0 最大 von Mises
    fixed_vm = [r[10] for r in rows if abs(r[1]) < tol]
    # 4) 固定端上/下表面
    fixed_top = [r[10] for r in rows if abs(r[1]) < tol and abs(r[3] - h) < tol]
    fixed_bot = [r[10] for r in rows if abs(r[1]) < tol and abs(r[3]) < tol]

    def mean(v):
        return sum(v) / len(v) if v else float("nan")

    lines = []
    lines.append("悬臂梁静力分析 —— CalculiX .frd 后处理结果")
    lines.append("=" * 60)
    lines.append(f"模型：{L:g} x {b:g} x {h:g} mm，左端固定，右端 100 N 沿 -Z")
    lines.append(f"材料：E={E:g} MPa，nu=0.3（CalculiX-Steel）")
    lines.append("")
    lines.append("1) 自由端 (x=100) 挠度 uz")
    lines.append(f"   FEA 最小值   = {tip_uz:.6e} mm  (|uz|max = {tip_abs:.6e} mm)")
    lines.append(f"   理论值       = {-DELTA_THEORY:.6e} mm")
    lines.append(f"   相对误差     = {abs(tip_abs - DELTA_THEORY) / DELTA_THEORY * 100:.2f}%")
    lines.append("")
    lines.append("2) 跨中 (x=50) von Mises 应力")
    lines.append(f"   上表面 z=10 : n={len(mid_top):4d}  平均 {mean(mid_top):8.3f} MPa  最大 {max(mid_top):8.3f} MPa")
    lines.append(f"   下表面 z= 0 : n={len(mid_bot):4d}  平均 {mean(mid_bot):8.3f} MPa  最大 {max(mid_bot):8.3f} MPa")
    lines.append(f"   理论值       = {SIGMA_THEORY(L / 2):.3f} MPa")
    lines.append("")
    lines.append("3) 固定端 (x=0) von Mises 应力")
    lines.append(f"   全部节点     : n={len(fixed_vm):4d}  最大 {max(fixed_vm):8.3f} MPa  平均 {mean(fixed_vm):8.3f} MPa")
    lines.append(f"   上表面 z=10 : n={len(fixed_top):4d}  平均 {mean(fixed_top):8.3f} MPa  最大 {max(fixed_top):8.3f} MPa")
    lines.append(f"   下表面 z= 0 : n={len(fixed_bot):4d}  平均 {mean(fixed_bot):8.3f} MPa  最大 {max(fixed_bot):8.3f} MPa")
    lines.append(f"   理论值       = {SIGMA_THEORY(0):.3f} MPa")
    lines.append("")
    lines.append("4) 全场最大位移 / 应力")
    umag = max(math.sqrt(r[11] ** 2 + r[12] ** 2 + r[13] ** 2) for r in rows)
    vm_max = max(r[10] for r in rows)
    lines.append(f"   |u|max = {umag:.6e} mm     von Mises max = {vm_max:.3f} MPa")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(OUT, "beam_summary.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")

    # ---------- 出图 ----------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 位移沿梁长：取中线 y=5 上表面 z=10 的节点，按 x 排序
    prof = sorted((r[1], -r[13]) for r in rows if abs(r[2] - b / 2) < tol and abs(r[3] - h) < tol)
    if prof:
        xs = [p[0] for p in prof]
        ds = [p[1] for p in prof]
        th = [DELTA_CURVE(x) for x in xs]
        fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
        ax.plot(xs, th, "k--", lw=1.5, label="Euler-Bernoulli theory")
        ax.plot(xs, ds, "o-", ms=3, lw=1.2, label="CalculiX C3D10")
        ax.set_xlabel("x [mm]")
        ax.set_ylabel("deflection uz [mm]")
        ax.set_title("Cantilever deflection along beam (top surface, y=5)")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        p1 = os.path.join(OUT, "beam_displacement.png")
        fig.savefig(p1)
        plt.close(fig)
        print(f"[OK] {p1}")

    # 应力沿梁长：上/下表面
    top = sorted((r[1], r[10]) for r in rows if abs(r[3] - h) < tol)
    bot = sorted((r[1], r[10]) for r in rows if abs(r[3]) < tol)
    if top and bot:
        xt = [p[0] for p in top]
        yt = [p[1] for p in top]
        xb = [p[0] for p in bot]
        yb = [p[1] for p in bot]
        xx = [i * L / 200.0 for i in range(201)]
        fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
        ax.plot(xx, [SIGMA_THEORY(x) for x in xx], "k--", lw=1.5, label="beam theory sigma(x)")
        ax.plot(xt, yt, ".", ms=2, alpha=0.6, label="FEA top surface z=10")
        ax.plot(xb, yb, ".", ms=2, alpha=0.6, label="FEA bottom surface z=0")
        ax.set_xlabel("x [mm]")
        ax.set_ylabel("von Mises stress [MPa]")
        ax.set_title("Bending stress along cantilever")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        p2 = os.path.join(OUT, "beam_stress.png")
        fig.savefig(p2)
        plt.close(fig)
        print(f"[OK] {p2}")


if __name__ == "__main__":
    main()
