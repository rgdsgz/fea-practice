# -*- coding: utf-8 -*-
"""002-L 形支架：解析 CalculiX .frd，提取位移/应力关键值。

用法: python postprocess_bracket.py <file.frd>
输出: bracket_summary.txt + bracket_topnodes.csv（同目录）
"""
import math
import os
import sys

FRD = sys.argv[1] if len(sys.argv) > 1 else r"D:\E\Model\项目\002-L形支架静力分析\03-计算\ccx\Unnamed\SolverCcxTools\FEMMeshGmsh.frd"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

nodes = {}      # nid -> (x, y, z)
disp = {}       # nid -> (ux, uy, uz)
stress = {}     # nid -> (sxx, syy, szz, sxy, syz, szx)

state = "nodes"
with open(FRD, "r", errors="replace") as f:
    for line in f:
        if line.startswith(" -4"):
            head = line[:40]
            if "DISP" in head:
                state, disp = "DISP", {}
            elif "STRESS" in head:
                state, stress = "STRESS", {}
            else:
                state = "other"
            continue
        if line.startswith(" -5") or line.startswith(" -3") or line.startswith("  1") or line.startswith("    1"):
            if line.startswith(" -3") and state == "nodes":
                state = "other"   # 节点块结束（后面是 "    3C" 单元块）
            continue
        if not line.startswith(" -1"):
            continue
        if state not in ("nodes", "DISP", "STRESS"):
            continue  # TOSTRAIN / ERROR 等块不解析
        body = line.rstrip("\n")
        nid = int(body[3:13])
        k = 3 if state == "nodes" else 6
        vals = []
        for i in range(k):
            seg = body[13 + 12 * i: 13 + 12 * (i + 1)]
            if not seg.strip():
                break
            vals.append(float(seg))
        if state == "nodes":
            if len(vals) >= 3:
                nodes[nid] = (vals[0], vals[1], vals[2])
        elif state == "DISP":
            if len(vals) >= 3:
                disp[nid] = (vals[0], vals[1], vals[2])
        elif state == "STRESS":
            if len(vals) >= 6:
                stress[nid] = tuple(vals[:6])


def vm(s):
    sxx, syy, szz, sxy, syz, szx = s
    return math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                     + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2))


lines = []
lines.append(f"FRD: {FRD}")
lines.append(f"节点数: {len(nodes)}, 位移节点: {len(disp)}, 应力节点: {len(stress)}")

# ---- 位移 ----
umax = max(disp.items(), key=lambda kv: math.sqrt(sum(v * v for v in kv[1])))
ux_min = min(disp.items(), key=lambda kv: kv[1][0])
lines.append("")
lines.append("== 位移 ==")
lines.append(f"合成位移最大: node {umax[0]} xyz={nodes[umax[0]]} |u|={math.sqrt(sum(v*v for v in umax[1])):.5f} mm, u=({umax[1][0]:.5f}, {umax[1][1]:.5f}, {umax[1][2]:.5f})")
lines.append(f"X 向位移最负: node {ux_min[0]} xyz={nodes[ux_min[0]]} ux={ux_min[1][0]:.5f} mm")

# 立板顶面 (z≈88) 的 ux 最大值
top = [(nid, d) for nid, d in disp.items() if abs(nodes[nid][2] - 88.0) < 0.05]
if top:
    top_min = min(top, key=lambda kv: kv[1][0])
    lines.append(f"立板顶面 (z=88) X 向最大挠度: node {top_min[0]} xyz={nodes[top_min[0]]} ux={top_min[1][0]:.5f} mm")

# ---- 应力 ----
vms = {nid: vm(s) for nid, s in stress.items()}
vmax = max(vms.items(), key=lambda kv: kv[1])
lines.append("")
lines.append("== von Mises 应力 ==")
lines.append(f"全场最大: node {vmax[0]} xyz={nodes[vmax[0]]} vm={vmax[1]:.2f} MPa")

# 圆角区域 x in [8, 16], z in [8, 16]
fillet = [(nid, v) for nid, v in vms.items()
          if 7.9 <= nodes[nid][0] <= 16.1 and 7.9 <= nodes[nid][2] <= 16.1]
if fillet:
    fm = max(fillet, key=lambda kv: kv[1])
    lines.append(f"圆角区域最大: node {fm[0]} xyz={nodes[fm[0]]} vm={fm[1]:.2f} MPa")
    lines.append(f"圆角区域节点数: {len(fillet)}")

# 立板根部截面 z in [8, 12]
root = [(nid, v) for nid, v in vms.items() if 7.9 <= nodes[nid][2] <= 12.1]
if root:
    rm = max(root, key=lambda kv: kv[1])
    lines.append(f"立板根部 (z=8~12) 最大: node {rm[0]} xyz={nodes[rm[0]]} vm={rm[1]:.2f} MPa")

# ---- 与手算对比 ----
E, L, I, F = 210000.0, 80.0, 60 * 8 ** 3 / 12, 500.0
delta = F * L ** 3 / (3 * E * I)
sigma = F * L * 4.0 / I
lines.append("")
lines.append("== 手算（立板当悬臂，不考虑底板/圆角） ==")
lines.append(f"挠度 δ=FL³/(3EI) = {delta:.4f} mm (L={L}, I={I})")
lines.append(f"根部弯曲应力 σ=FLc/I = {sigma:.2f} MPa")

text = "\n".join(lines)
print(text)
with open(os.path.join(OUT_DIR, "bracket_summary.txt"), "w", encoding="utf-8") as f:
    f.write(text + "\n")

# 应力前 30 节点 CSV
top30 = sorted(vms.items(), key=lambda kv: -kv[1])[:30]
with open(os.path.join(OUT_DIR, "bracket_topnodes.csv"), "w", encoding="utf-8") as f:
    f.write("node,x,y,z,vm_MPa,ux,uy,uz\n")
    for nid, v in top30:
        x, y, z = nodes[nid]
        u = disp.get(nid, (0, 0, 0))
        f.write(f"{nid},{x:.3f},{y:.3f},{z:.3f},{v:.3f},{u[0]:.6f},{u[1]:.6f},{u[2]:.6f}\n")
print("\n已写出 bracket_summary.txt / bracket_topnodes.csv")
