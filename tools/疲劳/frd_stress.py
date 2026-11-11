"""从 CalculiX 的 .frd 结果文件提取最后一个增量步的节点应力，输出 CSV。

用法：
    python frd_stress.py job.frd -o stress.csv

输出列：node, sxx, syy, szz, sxy, syz, szx  （单位与 .inp 输入一致，通常 MPa）

适用于：PrePoMax / FreeCAD FEM / 命令行 ccx 产生的 .frd。
"""
import argparse
import csv
import os
import sys

# 让脚本能直接用 tools\python_libs 里解压的可选依赖
_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIBS = os.path.join(_TOOLS, "python_libs")
if os.path.isdir(_LIBS) and _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

COMPONENT_ORDER = ["SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX"]


def parse_frd_stress(path):
    """返回 {node: [sxx, syy, szz, sxy, syz, szx]}，取文件中最后一个 STRESS 块。"""
    blocks = []
    cur = None
    components = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip("\n")
        s = line.strip()
        if s.startswith("-4"):
            parts = s.split()
            name = parts[1].upper() if len(parts) > 1 else ""
            if name == "STRESS":
                cur = {}
                components = []
                blocks.append(cur)
            else:
                cur = None
            i += 1
            continue
        if s.startswith("-5"):
            parts = s.split()
            if len(parts) >= 2:
                components.append(parts[1].upper())
            i += 1
            continue
        if s.startswith("-3"):
            cur = None
            components = []
            i += 1
            continue
        if s.startswith("-1") and cur is not None:
            # 定宽格式：line[3:13] = 节点号(%10d)，随后每 12 字符一个 %12.5E 值
            try:
                node = int(line[3:13])
            except ValueError:
                i += 1
                continue
            vals = []
            pos = 13
            while pos + 12 <= len(line):
                chunk = line[pos:pos + 12]
                pos += 12
                try:
                    vals.append(float(chunk))
                except ValueError:
                    pass
            cur.setdefault(node, []).extend(vals)
            i += 1
            continue
        i += 1

    if not blocks:
        raise SystemExit(f"没有在 {path} 里找到 STRESS 块")
    last = blocks[-1]
    if not components:
        components = COMPONENT_ORDER
    # 组件顺序对齐：SXX/SYY/SZZ/SXY/SYZ/SZX
    order = [components.index(c) if c in components else COMPONENT_ORDER.index(c)
             for c in COMPONENT_ORDER]
    out = {}
    for node, vals in last.items():
        if len(vals) < 6:
            continue
        out[node] = [vals[o] for o in order]
    return out


def main():
    ap = argparse.ArgumentParser(description="CalculiX .frd -> 节点应力 CSV")
    ap.add_argument("frd", help=".frd 文件路径")
    ap.add_argument("-o", "--out", default=None, help="输出 CSV（默认与 frd 同目录同名 .csv）")
    args = ap.parse_args()

    data = parse_frd_stress(args.frd)
    out = args.out or (args.frd.rsplit(".", 1)[0] + "_stress.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node"] + [c.lower() for c in COMPONENT_ORDER])
        for node in sorted(data):
            w.writerow([node] + [f"{v:.6g}" for v in data[node]])
    print(f"[OK] 提取 {len(data)} 个节点 -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
