"""003 四档网格收敛汇总 + 孔边厚度方向应力分布（最细网格）。"""
import math
import os
import sys

sys.path.insert(0, r"D:\E\Model\tools\疲劳")
from frd_stress import parse_frd_stress

RES = r"D:\E\Model\项目\003-带孔板应力集中与网格收敛\04-结果"
SIG_NOM = 10000.0 / (34.0 * 10.0)      # 29.41 MPa
KT_THEORY = 2.31
LEVELS = [
    ("1", "6 mm", "level1_6mm.inp", "level1_6mm.frd"),
    ("2", "4 mm", "level2_4mm.inp", "level2_4mm.frd"),
    ("3", "2.5 mm", "level3_2p5mm.inp", "level3_2p5mm.frd"),
    ("4", "1.5 mm", "level4_1p5mm.inp", "level4_1p5mm.frd"),
]


def read_inp(path):
    nodes, elems, mode = {}, 0, None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s.startswith("*"):
                low = s.lower()
                mode = "node" if low.startswith("*node") else ("elem" if low.startswith("*element") else None)
                continue
            if not s or mode is None:
                continue
            p = [q.strip() for q in s.split(",")]
            if mode == "node" and len(p) >= 4:
                nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
            elif mode == "elem" and len(p) >= 5:
                elems += 1
    return nodes, elems


def vm(t):
    sxx, syy, szz, sxy, syz, szx = t
    return math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                     + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2))


print(f"{'档':<3}{'尺寸':>7}{'节点':>9}{'体单元':>8}{'全场σmax':>10}{'Kt':>7}{'误差':>8}   峰值坐标")
print("-" * 88)
data = {}
for tag, size, inp, frd in LEVELS:
    ip, fp = os.path.join(RES, inp), os.path.join(RES, frd)
    if not (os.path.exists(ip) and os.path.exists(fp)):
        print(f"{tag:<3}{size:>7}   缺文件")
        continue
    nodes, nel = read_inp(ip)
    st = parse_frd_stress(fp)
    rows = sorted(((vm(t), nid, *nodes[nid]) for nid, t in st.items()), reverse=True)
    s, nid, x, y, z = rows[0]
    data[tag] = (nodes, st)
    print(f"{tag:<3}{size:>7}{len(nodes):>9}{nel:>8}{s:>10.2f}{s/SIG_NOM:>7.3f}"
          f"{(s-KT_THEORY*SIG_NOM)/(KT_THEORY*SIG_NOM)*100:>7.1f}%   ({x:.2f}, {y:.2f}, {z:.2f})")

nodes, st = data["4"]
rows = sorted(((vm(t), nid, *nodes[nid]) for nid, t in st.items()), reverse=True)
print("\n最细网格 1.5 mm：孔右侧边缘（x≈33, y≈60）沿厚度的 von Mises 分布")
print(f"{'z (mm)':>8}{'σvm max':>10}{'节点':>8}")
for zt in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 8.5, 9.0, 9.5, 10.0]:
    cand = [r for r in rows if abs(r[4] - zt) < 0.35 and abs(r[3] - 60.0) < 4.0 and r[2] > 25.0]
    if cand:
        c = cand[0]
        print(f"{zt:>8.2f}{c[0]:>10.2f}{c[1]:>8d}")

print("\n外推：最近两档 σmax 差值与相对变化")
l3 = max(vm(t) for t in data["3"][1].values())
l4 = max(vm(t) for t in data["4"][1].values())
print(f"  2.5 mm = {l3:.2f} MPa, 1.5 mm = {l4:.2f} MPa, 差 {l4-l3:+.2f} MPa "
      f"({(l4-l3)/l3*100:+.2f} %)")
