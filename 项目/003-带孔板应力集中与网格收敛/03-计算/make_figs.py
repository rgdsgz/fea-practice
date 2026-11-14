"""003 收敛图 + 净截面应力分布 + 表面 von Mises 云图（matplotlib，无 GUI）。"""
import math
import os
import sys

os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.dirname(__file__), ".mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for _f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    if os.path.exists(_f):
        font_manager.fontManager.addfont(_f)
plt.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, r"D:\E\Model\tools\疲劳")
from frd_stress import parse_frd_stress

RES = r"D:\E\Model\项目\003-带孔板应力集中与网格收敛\04-结果"
FIG = os.path.join(RES, "figs")
os.makedirs(FIG, exist_ok=True)
SIG_NOM = 10000.0 / (34.0 * 10.0)
KT = 2.31
LEVELS = [("1", 6.0, "level1_6mm"), ("2", 4.0, "level2_4mm"),
          ("3", 2.5, "level3_2p5mm"), ("4", 1.5, "level4_1p5mm")]


def read_inp(path):
    nodes, mode = {}, None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s.startswith("*"):
                mode = "node" if s.lower().startswith("*node") else None
                continue
            if mode != "node" or not s:
                continue
            p = [q.strip() for q in s.split(",")]
            if len(p) >= 4:
                nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
    return nodes


def vm(t):
    sxx, syy, szz, sxy, syz, szx = t
    return math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                     + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2))


data = {}
for tag, h, base in LEVELS:
    nodes = read_inp(os.path.join(RES, base + ".inp"))
    st = parse_frd_stress(os.path.join(RES, base + ".frd"))
    data[tag] = (h, nodes, st)
    print(f"[{tag}] {h} mm: {len(nodes)} 节点")

# 1) 收敛曲线
fig, ax = plt.subplots(figsize=(6.4, 4.2))
hs = [data[t][0] for t in "1234"]
smax = [max(vm(v) for v in data[t][2].values()) for t in "1234"]
ax.plot(hs, smax, "o-", lw=1.8, ms=7, label="FEA 全场最大值")
ax.axhline(KT * SIG_NOM, ls="--", c="crimson", lw=1.4, label=f"理论 2D 值 {KT*SIG_NOM:.2f} MPa")
for x, y in zip(hs, smax):
    ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(6, -12), fontsize=9)
ax.set_xlabel("网格尺寸 h (mm)")
ax.set_ylabel("孔边最大 von Mises (MPa)")
ax.set_title("带孔板应力集中：网格收敛性 (h 越小网格越密)")
ax.invert_xaxis()
ax.grid(alpha=0.3)
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "convergence.png"), dpi=150)
plt.close(fig)

# 2) 净截面 σyy 分布（y = 60）
fig, ax = plt.subplots(figsize=(7.2, 4.2))
for tag, col in zip("1234", ["#9ecae1", "#4292c6", "#2171b5", "#08306b"]):
    h, nodes, st = data[tag]
    pts = []
    for nid, t in st.items():
        x, y, z = nodes[nid]
        if abs(y - 60.0) < 0.6 and z > 4.9:
            pts.append((x, t[1]))
    if not pts:
        continue
    pts.sort()
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", ms=2.5, lw=1.2,
            color=col, label=f"{h} mm")
ax.axhline(SIG_NOM, ls=":", c="gray", lw=1)
ax.set_xlabel("x (mm)   [y = 60, 板厚中部]")
ax.set_ylabel("SYY (MPa)")
ax.set_title("净截面应力分布：孔边尖峰与收敛过程")
ax.grid(alpha=0.3)
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "net_section.png"), dpi=150)
plt.close(fig)

# 3) 最细网格表面 von Mises 云图 (z = 0 面)
h, nodes, st = data["4"]
xs, ys, cs = [], [], []
for nid, t in st.items():
    x, y, z = nodes[nid]
    if z < 1e-6 and 7.9 <= math.hypot(x - 25.0, y - 60.0) <= 60.0:
        xs.append(x)
        ys.append(y)
        cs.append(vm(t))
fig, ax = plt.subplots(figsize=(5.0, 7.4))
sc = ax.scatter(xs, ys, c=cs, s=6, cmap="turbo")
ax.add_patch(plt.Circle((25, 60), 8, fill=False, color="k", lw=1.2))
ax.set_aspect("equal")
ax.set_xlabel("x (mm)")
ax.set_ylabel("y (mm)")
ax.set_title(f"von Mises 云图（h={h} mm，z=0 表面）")
fig.colorbar(sc, ax=ax, label="MPa", shrink=0.7)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "contour_surface.png"), dpi=150)
plt.close(fig)

print("[OK] 图已写入", FIG)
