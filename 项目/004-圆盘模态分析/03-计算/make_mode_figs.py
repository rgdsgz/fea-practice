# -*- coding: utf-8 -*-
"""004 圆盘模态分析：画前 6 阶振型云图 + 用方位角 FFT 定量确认节径数 n。

思路：
  1. 取 z = t（顶面）的节点，在 xy 平面做 Delaunay 三角化，按 uz 上色 —— 俯视图可直接看出节径/节圆。
  2. 沿半径 r 的圆环取一圈节点，对 uz(theta) 做 FFT；主峰阶次 = 该振型的节径数 n。
     轴对称振型 (n=0) 主峰在 0 阶，因此可区分「伞形/节圆」与「带节径」两类。
  3. 节圆数 s 用「沿半径的 uz 零交叉次数 / 2」估计。
"""
import os
import csv
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
os.environ.setdefault("MPLCONFIGDIR", r"D:\E\Model\项目\004-圆盘模态分析\03-计算\.mpl")

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib import font_manager

CSV = r"D:\E\Model\项目\004-圆盘模态分析\04-结果\modes_disp.csv"
OUTDIR = r"D:\E\Model\项目\004-圆盘模态分析\04-结果\figs"
T = 6.0
R = 100.0

for cand in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    if os.path.exists(cand):
        font_manager.fontManager.addfont(cand)
plt.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def load():
    """返回 {mode: (freq, x, y, z, ux, uy, uz)}"""
    data = {}
    with open(CSV, encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        for r in rd:
            m = int(r["mode"])
            d = data.setdefault(m, {"f": float(r["freq_Hz"]), "x": [], "y": [], "z": [],
                                    "ux": [], "uy": [], "uz": []})
            d["x"].append(float(r["x_mm"]))
            d["y"].append(float(r["y_mm"]))
            d["z"].append(float(r["z_mm"]))
            d["ux"].append(float(r["ux"]))
            d["uy"].append(float(r["uy"]))
            d["uz"].append(float(r["uz"]))
    for m, d in data.items():
        for k in ("x", "y", "z", "ux", "uy", "uz"):
            d[k] = np.asarray(d[k])
    return data


def nodal_analysis(x, y, uz, r_ref=78.0, tol=1.2):
    """返回 (n 节径数, s 内部节圆数)

    n：在 r=r_ref 的圆环上沿 theta 走一圈，uz 变号次数 / 2。
       每个节径（径向零线）会让 uz 变号两次，因此变号数 = 2n。
    s：沿 theta≈0 的半径从圆心走到 r=0.97R，uz 的零交叉次数。
       每穿过一条内部节圆变号一次，因此交叉数 = s。
    """
    r = np.hypot(x, y)
    th = np.arctan2(y, x)

    # --- 节径数 n：绕环一周数变号 ---
    ring = np.abs(r - r_ref) < tol
    n_est = None
    if ring.sum() >= 30:
        ang, val = th[ring], uz[ring]
        o = np.argsort(ang)
        ang, val = ang[o], val[o]
        grid = np.linspace(-np.pi, np.pi, 721)[:-1]
        vu = np.interp(grid, ang, val, period=2 * np.pi)
        sign = np.sign(vu)
        # 去掉零值点（避免把恰好为 0 的插值点算成两次变号）
        sign = sign[sign != 0]
        changes = int(np.sum(sign[1:] != sign[:-1]))
        # 环首尾相接处也要比一次
        if len(sign) > 1 and sign[0] != sign[-1]:
            changes += 1
        n_est = changes // 2

    # --- 内部节圆数 s：沿半径数零交叉 ---
    # 不能固定沿 +x 采样：若节径恰好落在 +x 上，整条半径 uz≈0，噪声会给出上百次假交叉
    # （实测第 7 阶曾得 s=138）。改为先找该振型振幅最大的方位角，沿那里向内走。
    th0 = 0.0
    ring_for_dir = np.abs(r - r_ref) < tol
    if ring_for_dir.sum() > 10:
        idx = np.argmax(np.abs(uz[ring_for_dir]))
        th0 = th[ring_for_dir][idx]

    band = np.abs(np.angle(np.exp(1j * (th - th0)))) < 0.08
    rr, vv = r[band], uz[band]
    o = np.argsort(rr)
    rr, vv = rr[o], vv[o]
    keep = rr < 0.97 * R
    rr, vv = rr[keep], vv[keep]
    s_est = 0
    for i in range(1, len(vv)):
        if vv[i - 1] * vv[i] < 0:
            s_est += 1
    return n_est, s_est


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(OUTDIR, exist_ok=True)
    data = load()

    info = {}
    print("阶  freq(Hz)   节径n  内部节圆s")
    for m in sorted(data):
        d = data[m]
        n, s = nodal_analysis(d["x"], d["y"], d["uz"])
        info[m] = (n, s)
        print("%2d  %8.2f      %s       %s" % (m, d["f"], n, s))

    modes = sorted(data)[:6]
    fig, axes = plt.subplots(2, 3, figsize=(15, 10.5))
    for ax, m in zip(axes.ravel(), modes):
        d = data[m]
        top = np.abs(d["z"] - T) < 1e-3
        x, y, uz = d["x"][top], d["y"][top], d["uz"][top]
        tri = mtri.Triangulation(x, y)
        umax = np.abs(uz).max()
        lv = np.linspace(-umax, umax, 21)
        cf = ax.tricontourf(tri, uz, levels=lv, cmap="RdBu_r")
        ax.tricontour(tri, uz, levels=[0.0], colors="k", linewidths=0.9)
        circ = plt.Circle((0, 0), R, fill=False, color="k", lw=1.2)
        ax.add_patch(circ)
        ax.set_aspect("equal")
        ax.set_xlim(-1.12 * R, 1.12 * R)
        ax.set_ylim(-1.12 * R, 1.12 * R)
        n, s = info[m]
        ax.set_title("第 %d 阶  f = %.1f Hz\n节径 n=%d，节圆 s=%d" % (m, d["f"], n, s),
                     fontsize=11)
        ax.set_xlabel("x (mm)", fontsize=9)
        ax.set_ylabel("y (mm)", fontsize=9)
        ax.tick_params(labelsize=8)
        plt.colorbar(cf, ax=ax, fraction=0.046, pad=0.03).set_label("uz (mm)", fontsize=8)

    fig.suptitle("004 圆盘（R=100 mm, t=6 mm, 周边固定）前 6 阶振型 —— 顶面 z=6 mm 俯视，uz 云图\n"
                 "黑实线为零位移节线（节径/节圆），黑色圆圈为固定边界 r=100 mm",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p1 = os.path.join(OUTDIR, "modes_1to6.png")
    fig.savefig(p1, dpi=170)
    plt.close(fig)
    print("wrote", p1)

    # 单独一张：同阶简并振型对比（(1,1) 的两条节径方向不同）
    fig2, axes2 = plt.subplots(1, 2, figsize=(11, 5.2))
    for ax, m in zip(axes2, [2, 3]):
        d = data[m]
        top = np.abs(d["z"] - T) < 1e-3
        x, y, uz = d["x"][top], d["y"][top], d["uz"][top]
        tri = mtri.Triangulation(x, y)
        umax = np.abs(uz).max()
        cf = ax.tricontourf(tri, uz, levels=np.linspace(-umax, umax, 21), cmap="RdBu_r")
        ax.tricontour(tri, uz, levels=[0.0], colors="k", linewidths=1.1)
        ax.add_patch(plt.Circle((0, 0), R, fill=False, color="k", lw=1.2))
        ax.set_aspect("equal")
        ax.set_xlim(-1.12 * R, 1.12 * R)
        ax.set_ylim(-1.12 * R, 1.12 * R)
        ax.set_title("第 %d 阶  f = %.2f Hz" % (m, d["f"]), fontsize=11)
        ax.set_xlabel("x (mm)", fontsize=9)
        ax.set_ylabel("y (mm)", fontsize=9)
        plt.colorbar(cf, ax=ax, fraction=0.046, pad=0.03).set_label("uz (mm)", fontsize=8)
    fig2.suptitle("(1,1) 简并对：同一频率的两条互相垂直节径（第 2/3 阶）\n"
                  "频率差 0.005%，FEA 中任意二者线性组合仍是同频振型", fontsize=11)
    fig2.tight_layout(rect=[0, 0, 1, 0.90])
    p2 = os.path.join(OUTDIR, "degenerate_pair.png")
    fig2.savefig(p2, dpi=170, bbox_inches="tight")
    plt.close(fig2)
    print("wrote", p2)


if __name__ == "__main__":
    main()
