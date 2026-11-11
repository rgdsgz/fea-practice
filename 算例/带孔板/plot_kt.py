"""把带孔板算例的 von Mises 应力画成云图（自由表面 z=5 和 z=0）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(TOOLS, "tools", "疲劳"))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(HERE, ".mplcache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from frd_stress import parse_frd_stress
from run_kt import parse_gmsh_inp, vm

MESH = os.path.join(HERE, "plate_hole_l2.inp")
FRD = os.path.join(HERE, "plate_hole_ccx.frd")


def main():
    nodes, _ = parse_gmsh_inp(MESH)
    data = parse_frd_stress(FRD)
    xs, ys, vs = [], [], []
    for nid, t in data.items():
        if nid not in nodes:
            continue
        x, y, z = nodes[nid]
        if z > 4.99:  # 自由表面 z=5
            xs.append(x)
            ys.append(y)
            vs.append(vm(t))
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=150)
    sc = ax.scatter(xs, ys, c=vs, s=6, cmap="turbo", vmin=0, vmax=max(vs))
    fig.colorbar(sc, ax=ax, label="von Mises [MPa]")
    ax.set_aspect("equal")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_title(f"Plate with central hole, tension 100 MPa - von Mises on z=5 surface "
                 f"(max {max(vs):.1f} MPa)")
    out = os.path.join(HERE, "kt_stress_contour.png")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print("[OK]", out, "max", round(max(vs), 1))


if __name__ == "__main__":
    main()
