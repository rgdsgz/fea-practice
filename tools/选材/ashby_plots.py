"""根据本地材料库绘制 Ashby 材料性能图（E-ρ、σy-ρ）。

用法（FreeCAD 自带 Python，含 matplotlib/numpy）：
    F:\\FreeCAD\\bin\\python.exe "D:\\E\\Model\\tools\\选材\\ashby_plots.py"

输出：
    D:\\E\\Model\\tools\\选材\\ashby_E_rho.png
    D:\\E\\Model\\tools\\选材\\ashby_sy_rho.png
"""
import os
import sqlite3

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(OUT_DIR, "materials.db")
# 沙箱/受限环境下 matplotlib 默认缓存目录可能不可写，统一放到脚本旁边
os.environ.setdefault("MPLCONFIGDIR", os.path.join(OUT_DIR, ".mplcache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CATEGORY_COLORS = {
    "Metal": "#1f77b4",
    "Thermoplast": "#d62728",
    "Glass": "#2ca02c",
    "Carbon": "#7f7f7f",
    "Aggregate": "#bcbd22",
    "Wood": "#8c564b",
    "Standard": "#9467bd",
}


def load():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"找不到 {DB_PATH}，先运行 build_materials.py")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM materials")]
    conn.close()
    return rows


def scatter_plot(rows, x_key, y_key, xlabel, ylabel, title, outfile, index_lines=None):
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=150)
    seen = set()
    annotated_metal = [0]
    for r in rows:
        x, y = r[x_key], r[y_key]
        if not x or not y or x <= 0 or y <= 0:
            continue
        cat = r["category"] if r["category"] in CATEGORY_COLORS else "Standard"
        label = cat if cat not in seen else None
        seen.add(cat)
        ax.scatter(x, y, s=42, alpha=0.85, color=CATEGORY_COLORS[cat],
                   edgecolors="white", linewidths=0.4, label=label, zorder=3)
        # 标注关键条目（避免图太乱：跳过 EN- 开头的标准牌号，金属最多标 8 个）
        name = r["name"] or ""
        if cat == "Thermoplast" or (cat == "Metal" and not name.startswith("EN-")):
            if cat == "Metal":
                annotated_metal[0] += 1
                if annotated_metal[0] > 8:
                    continue
            ax.annotate(name, (x, y), fontsize=6, color="#333333",
                        xytext=(3, 2), textcoords="offset points")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, which="both", ls=":", lw=0.5, alpha=0.6)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)

    if index_lines:
        xs = np.logspace(np.log10(ax.get_xlim()[0]), np.log10(ax.get_xlim()[1]), 50)
        for m, label in index_lines:
            # 性能指数 M = y / x^m  =>  y = M * x^m 的等值线族
            base = np.median([r[y_key] / (r[x_key] ** m) for r in rows
                              if r[x_key] and r[y_key] and r[x_key] > 0])
            for factor in (0.3, 1.0, 3.0):
                ax.plot(xs, base * factor * xs ** m, ls="--", lw=0.7, color="#777777", alpha=0.7)
        ax.text(0.99, 0.02, "dashed lines = constant " + ", ".join(l for _, l in index_lines),
                transform=ax.transAxes, ha="right", fontsize=7, color="#666666")

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, outfile))
    plt.close(fig)
    print("[OK]", os.path.join(OUT_DIR, outfile))


def main():
    rows = load()
    print(f"材料条数: {len(rows)}")
    scatter_plot(
        rows, "density_kg_m3", "E_GPa",
        "Density  rho  [kg/m^3]",
        "Young's modulus  E  [GPa]",
        "Ashby chart: Stiffness vs Density (FreeCAD material cards)",
        "ashby_E_rho.png",
        index_lines=[(0.5, "E^0.5/rho"), (1.0, "E/rho")],
    )
    scatter_plot(
        rows, "density_kg_m3", "yield_MPa",
        "Density  rho  [kg/m^3]",
        "Yield strength  sigma_y  [MPa]",
        "Ashby chart: Strength vs Density (FreeCAD material cards)",
        "ashby_sy_rho.png",
        index_lines=[(1.0, "sigma_y/rho")],
    )


if __name__ == "__main__":
    main()
