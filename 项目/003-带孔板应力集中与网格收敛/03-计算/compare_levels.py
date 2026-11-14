"""003 网格收敛对比：三档 .frd 的孔边峰值（全场 / 中厚面）。"""
import math
import os
import sys

sys.path.insert(0, r"D:\E\Model\tools\疲劳")
from frd_stress import parse_frd_stress

RES = r"D:\E\Model\项目\003-带孔板应力集中与网格收敛\04-结果"
SIG_NOM = 10000.0 / (34.0 * 10.0)
HOLE = (25.0, 60.0)


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


print(f"{'档':<4}{'尺寸':>7}{'节点':>8}{'单元':>7}{'全场σmax':>11}{'Kt':>8}{'中厚面σmax':>12}{'Kt':>8}{'位置':>22}")
print("-" * 92)
for tag, size, inp, frd in [
    ("1", "6 mm", "level1_6mm.inp", "level1_6mm.frd"),
    ("2", "4 mm", "level2_4mm.inp", "level2_4mm.frd"),
    ("3", "2.5 mm", "level3_2p5mm.inp", "level3_2p5mm.frd"),
]:
    ip, fp = os.path.join(RES, inp), os.path.join(RES, frd)
    if not (os.path.exists(ip) and os.path.exists(fp)):
        print(tag, "缺文件", ip, fp)
        continue
    nodes, nel = read_inp(ip)
    st = parse_frd_stress(fp)
    rows = [(vm(t), nid, *nodes[nid]) for nid, t in st.items()]
    rows.sort(reverse=True)
    top = rows[0]
    mid = [r for r in rows if abs(r[4] - 5.0) < 0.6]
    mtop = mid[0]
    print(f"{tag:<4}{size:>7}{len(nodes):>8}{nel:>7}{top[0]:>11.2f}{top[0]/SIG_NOM:>8.3f}"
          f"{mtop[0]:>12.2f}{mtop[0]/SIG_NOM:>8.3f}   ({top[2]:.2f},{top[3]:.2f},{top[4]:.2f})")
