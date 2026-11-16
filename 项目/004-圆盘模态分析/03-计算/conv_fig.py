# -*- coding: utf-8 -*-
"""004 圆盘模态分析：网格收敛曲线 + Richardson 外推"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
os.environ.setdefault("MPLCONFIGDIR", r"D:\E\Model\项目\004-圆盘模态分析\03-计算\.mpl")

import matplotlib.pyplot as plt
from matplotlib import font_manager

OUTDIR = r"D:\E\Model\项目\004-圆盘模态分析\04-结果\figs"
for cand in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    if os.path.exists(cand):
        font_manager.fontManager.addfont(cand)
plt.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 三档结果（h mm -> 前 6 阶 Hz）
DATA = {
    4.0: [1513.83, 3125.23, 3125.44, 5080.58, 5080.77, 5780.28],
    3.0: [1511.64, 3117.91, 3117.91, 5062.69, 5062.94, 5759.01],
    2.0: [1510.45, 3114.97, 3114.97, 5057.19, 5057.20, 5752.39],
}
HS = sorted(DATA)
NAMES = ["f1 (0,1) 伞形", "f2 (1,1)", "f3 (1,1)", "f4 (2,1)", "f5 (2,1)", "f6 (0,2)"]


def richardson(f_coarse, f_mid, f_fine, h_coarse, h_mid, h_fine, p=2.0):
    """三档网格 Richardson 外推。

    注意：本算例两段细化比不同（4/3 = 1.33，3/2 = 1.5），不能用等比的
    p = log2((fc-fm)/(fm-ff)) 反推阶次。这里按 C3D10 二次单元的理论阶次 p=2，
    用最后一对网格外推：f_ex = f_fine + (f_fine - f_mid) / (r^p - 1)，r = h_mid/h_fine。
    """
    r = h_mid / h_fine
    f_ex = f_fine + (f_fine - f_mid) / (r ** p - 1)
    return f_ex


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(OUTDIR, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4))

    # 左图：归一化频率 (f/f_extrap - 1)，把四条曲线放到同一尺度看收敛
    ax = axes[0]
    hs = np.array(HS)
    for i, name in enumerate(NAMES[:4]):
        fex = richardson(DATA[4.0][i], DATA[3.0][i], DATA[2.0][i], 4.0, 3.0, 2.0)
        ys = [(DATA[h][i] - fex) / fex * 100 for h in HS]
        ax.plot(hs, ys, "o-", lw=1.8, ms=7, label=name)
    ax.axhline(0, color="k", lw=0.8, ls="--", alpha=0.6)
    ax.set_xlabel("网格尺寸 h (mm)", fontsize=11)
    ax.set_ylabel("相对外推值 (h→0) 的偏差 (%)", fontsize=11)
    ax.set_title("频率随网格加密的收敛趋势", fontsize=11)
    ax.grid(alpha=0.3)
    ax.set_xlim(4.2, 1.9)          # h 变细向右，收敛图惯例
    ax.set_ylim(-0.05, 0.62)
    ax.legend(fontsize=9, loc="lower left")
    ax.set_xticks(hs)

    # 右图：双对数，斜率 = 收敛阶次（二阶单元应 ≈ 2）
    ax2 = axes[1]
    for i, name in enumerate(NAMES[:4]):
        fex = richardson(DATA[4.0][i], DATA[3.0][i], DATA[2.0][i], 4.0, 3.0, 2.0)
        errs = [abs(DATA[h][i] - fex) / fex * 100 for h in HS]
        ax2.loglog(hs, errs, "o-", lw=1.8, ms=7, label=name)
        k = np.polyfit(np.log(hs), np.log(errs), 1)[0]
        print("  %-14s 实测收敛阶次 ≈ %.2f" % (name, k))
    # 参考斜率 2
    href = np.array([2.0, 4.0])
    ax2.loglog(href, errs[0] * (href / 2.0) ** 2, "k:", lw=1.2, label="参考 h²")
    ax2.set_xlabel("网格尺寸 h (mm)", fontsize=11)
    ax2.set_ylabel("绝对偏差 (%)", fontsize=11)
    ax2.set_title("收敛阶次（双对数，斜率 = 阶次）", fontsize=11)
    ax2.set_xticks(hs)
    ax2.set_xticklabels(["4", "3", "2"])
    ax2.minorticks_off()
    ax2.grid(alpha=0.3, which="both")
    ax2.invert_xaxis()
    ax2.legend(fontsize=9)

    fig.suptitle("004 圆盘模态分析 —— 三档网格（4 / 3 / 2 mm）收敛性", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    p = os.path.join(OUTDIR, "convergence.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    print("wrote", p)

    # Richardson 外推（按 h^2，用 3mm/2mm 那一对）
    print("\n%-14s %-11s %-11s %-11s %-11s %-9s" %
          ("阶", "h=4mm", "h=3mm", "h=2mm", "外推(h→0)", "h=2mm 残差"))
    print("-" * 78)
    for i, name in enumerate(NAMES):
        fex = richardson(DATA[4.0][i], DATA[3.0][i], DATA[2.0][i], 4.0, 3.0, 2.0)
        res = abs(DATA[2.0][i] - fex) / fex * 100
        print("%-14s %-11.2f %-11.2f %-11.2f %-11.2f %-9s"
              % (name, DATA[4.0][i], DATA[3.0][i], DATA[2.0][i], fex, "%.3f%%" % res))
    print("\n收敛判定：h=3mm 相对 h=2mm 偏差 0.08%~0.12%；")
    print("          按 C3D10 二次收敛（p=2）外推到 h→0，h=2mm 的残差 < 0.10%，")
    print("          即 2mm 网格的结果已可作为收敛值使用。")


if __name__ == "__main__":
    main()
