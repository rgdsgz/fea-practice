"""疲劳评定（高周疲劳 S-N 法 + Miner 线性损伤累积）。

输入：节点应力 CSV（来自 frd_stress.py），列：node, sxx, syy, szz, sxy, syz, szx（MPa）

两种模式：
  1) 恒幅：只给最大载荷工况应力 + 应力比 R（默认 0 = 脉动循环）
        python fatigue.py stress.csv --uts 400 --ratio 0
  2) 变幅：给最大载荷工况应力 + 载荷谱 CSV（两列：scale,n_cycles），
     每个谱块按 scale 缩放应力幅后累积损伤
        python fatigue.py stress.csv --uts 400 --ratio 0 --spectrum spectrum.csv

S-N 参数优先级：
  1) --sigma-f 与 --b 直接给 Basquin 参数：sigma_a = sigma_f * (2N)^b
  2) 否则用 Shigley 工程估算：Se = 0.5*UTS（钢），S1000 = 0.9*UTS，
     a = (f*UTS)^2/Se，b = -1/3*log10(f*UTS/Se)，N = (sigma_a/a)^(1/b)
  材料数据库（tools/选材/materials.db）里有 sigma_f / b / Se 时可用 --material 名称自动读取。

平均应力修正：--method goodman|gerber|swt|none
"""
import argparse
import csv
import os
import sqlite3
import sys

# 让脚本能直接用 tools\python_libs 里解压的可选依赖
_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIBS = os.path.join(_TOOLS, "python_libs")
if os.path.isdir(_LIBS) and _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = _TOOLS
DB_PATH = os.path.join(TOOLS, "选材", "materials.db")


def vm(t):
    """von Mises 等效应力，t = [sxx, syy, szz, sxy, syz, szx]"""
    sxx, syy, szz, sxy, syz, szx = t
    return float(np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2)
    ))


def load_stress_csv(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "node": int(r["node"]),
                    "t": [float(r["sxx"]), float(r["syy"]), float(r["szz"]),
                          float(r["sxy"]), float(r["syz"]), float(r["szx"])],
                })
            except (KeyError, ValueError):
                continue
    if not rows:
        raise SystemExit(f"{path} 里没有可用数据")
    return rows


def material_from_db(name):
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM materials WHERE name LIKE ? LIMIT 1", (f"%{name}%",)
        ).fetchone()
    except sqlite3.Error:
        row = None
    conn.close()
    return dict(row) if row else None


def shigley_sn(uts, se_factor=0.5):
    """返回 (a, b)，S-N: sigma_a = a * N^b"""
    se = se_factor * uts
    f = 0.9
    a = (f * uts) ** 2 / se
    b = -(1.0 / 3.0) * np.log10(f * uts / se)
    return a, b


def sn_life(sigma_a, sigma_f, b):
    """Basquin: sigma_a = sigma_f * (2N)^b  =>  N"""
    if sigma_a <= 0:
        return float("inf")
    two_n = (sigma_a / sigma_f) ** (1.0 / b)
    return two_n / 2.0


def mean_stress_correction(sa, sm, uts, method):
    if method == "none":
        return sa
    if method == "goodman":
        return sa / max(1.0 - sm / uts, 1e-6) if sm > 0 else sa
    if method == "gerber":
        return sa / max(1.0 - (sm / uts) ** 2, 1e-6) if sm > 0 else sa
    if method == "swt":
        smax = sa + sm
        return float(np.sqrt(max(smax, 0.0) * sa))
    raise SystemExit(f"未知修正方法 {method}")


def main():
    ap = argparse.ArgumentParser(description="高周疲劳 S-N 评定")
    ap.add_argument("stress_csv", help="最大载荷工况的节点应力 CSV")
    ap.add_argument("--ratio", type=float, default=0.0, help="应力比 R = sigma_min/sigma_max（默认 0）")
    ap.add_argument("--uts", type=float, default=None, help="抗拉强度 MPa（用于 Shigley 估算/Goodman）")
    ap.add_argument("--sigma-f", type=float, default=None, help="Basquin 疲劳强度系数 sigma_f'（MPa）")
    ap.add_argument("--b", type=float, default=None, help="Basquin 疲劳强度指数（负值）")
    ap.add_argument("--material", default=None, help="材料名（从 materials.db 读取 sigma_f/b/Se 或 UTS）")
    ap.add_argument("--se-factor", type=float, default=0.5, help="Se/UTS 比例（钢 0.5，默认）")
    ap.add_argument("--method", default="goodman", choices=["goodman", "gerber", "swt", "none"])
    ap.add_argument("--spectrum", default=None, help="载荷谱 CSV：scale,n_cycles")
    ap.add_argument("-o", "--out", default=None, help="结果 CSV")
    args = ap.parse_args()

    rows = load_stress_csv(args.stress_csv)

    # 材料参数
    mat = material_from_db(args.material) if args.material else None
    uts = args.uts or (mat["uts_MPa"] if mat else None)
    sigma_f = args.sigma_f or (mat["sigma_f_MPa"] if mat else None)
    b = args.b or (mat["b"] if mat else None)
    use_basquin = sigma_f is not None and b is not None
    if not use_basquin:
        if not uts:
            raise SystemExit("需要 --uts 或 --sigma-f/--b 或 --material")
        a, b = shigley_sn(uts, args.se_factor)
        print(f"[info] 使用 Shigley 估算 S-N: a={a:.1f} MPa, b={b:.4f} (UTS={uts} MPa)")
    else:
        print(f"[info] 使用 Basquin: sigma_f'={sigma_f} MPa, b={b}")

    # 载荷谱
    spectrum = None
    if args.spectrum:
        spectrum = []
        with open(args.spectrum, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                spectrum.append((float(r["scale"]), float(r["n_cycles"])))
        if not spectrum:
            raise SystemExit("载荷谱为空")

    R = args.ratio
    results = []
    for row in rows:
        t_max = row["t"]
        t_min = [R * v for v in t_max]
        t_a = [(mx - mn) / 2.0 for mx, mn in zip(t_max, t_min)]
        t_m = [(mx + mn) / 2.0 for mx, mn in zip(t_max, t_min)]
        sa = vm(t_a)
        sm = vm(t_m)
        sa_c = mean_stress_correction(sa, sm, uts if uts else 1.0, args.method)

        def life(sa_eq):
            if use_basquin:
                return sn_life(sa_eq, sigma_f, b)
            return (sa_eq / a) ** (1.0 / b) if sa_eq > 0 else float("inf")

        if spectrum is None:
            n_cycles = 1e7  # 参考循环数，用于判断是否超过 1e7 次的"无限寿命"阈值
            nf = life(sa_c)
            damage = n_cycles / nf if np.isfinite(nf) else 0.0
            results.append((row["node"], sa, sm, sa_c, nf, damage))
        else:
            damage = 0.0
            nf_at_sa = life(sa_c)
            for scale, n_i in spectrum:
                sa_i = mean_stress_correction(vm([scale * v for v in t_a]),
                                              vm([scale * v for v in t_m]),
                                              uts if uts else 1.0, args.method)
                nf_i = life(sa_i)
                damage += n_i / nf_i if np.isfinite(nf_i) else 0.0
            results.append((row["node"], sa, sm, sa_c, nf_at_sa, damage))

    # 最危险点
    results.sort(key=lambda r: -r[5])
    worst = results[0]
    out = args.out or (os.path.splitext(args.stress_csv)[0] + "_fatigue.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node", "sigma_a_MPa", "sigma_m_MPa", "sigma_a_corrected_MPa", "N_cycles", "damage"])
        for node, sa, sm, sac, nf, d in results:
            w.writerow([node, f"{sa:.3f}", f"{sm:.3f}", f"{sac:.3f}",
                        f"{nf:.3e}" if np.isfinite(nf) else "inf", f"{d:.4e}"])

    print(f"[OK] 评定 {len(results)} 个节点 -> {out}")
    print(f"最危险节点: node {worst[0]}  sigma_a={worst[1]:.2f} MPa  "
          f"sigma_m={worst[2]:.2f} MPa  修正后={worst[3]:.2f} MPa  "
          f"N={worst[4]:.3e}  damage={worst[5]:.3e}")
    if worst[5] >= 1.0:
        print(f"[WARN] 最大损伤 {worst[5]:.2f} >= 1，按 Miner 判据已疲劳失效")
    else:
        print(f"[OK] 安全系数（按损伤倒数）≈ {1.0/worst[5]:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
