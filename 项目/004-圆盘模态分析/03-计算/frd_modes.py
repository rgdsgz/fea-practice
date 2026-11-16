# -*- coding: utf-8 -*-
"""004 圆盘模态分析：从 CalculiX .frd 提取振型位移场并画云图。

.frd 结构：每个模态（step）含 4 个结果块：DISP / STRESS / TOSTRAIN / ERROR。
块以 -4 开头、-3 结束，数据行以 -1 开头，固定宽度 12 字符一列。
"""
import os
import sys
import numpy as np

FRD = r"D:\E\Model\fem004\Disc\SolverCcxTools001\FEMMeshGmsh.frd"
OUT_CSV = r"D:\E\Model\项目\004-圆盘模态分析\04-结果\modes_disp.csv"

# 只需要前 N 阶
NMODES = 10


def parse_frd(path):
    """返回 (node_ids, coords[N,3], blocks, freqs)

    .frd 里 ` -1` 开头的数据行在三个不同区块里含义完全不同：
      * 节点块（以 ` 2C` 开头）：节点号 + xyz
      * 单元块（以 ` 3C` 开头）：单元号 + 类型 + 节点（不是坐标！）
      * 结果块（以 ` -4` 开头）：节点号 + 各分量
    必须用状态机区分，否则单元行会被当坐标解析而崩掉。
    """
    coords = {}
    node_order = []
    blocks = []          # [(mode, kind, {nid: tuple})]
    cur_kind = None
    cur_data = {}
    mode_no = 0
    state = "none"
    freqs = {}

    with open(path, "r", errors="replace") as fh:
        for line in fh:
            if len(line) < 4:
                continue
            tag = line[0:3]
            head = line.strip()
            if head[:2] == "2C":
                state = "nodes"
                continue
            if head[:2] == "3C":
                state = "elem"
                continue
            if tag == " -4":                      # 结果块开始
                state = "result"
                cur_kind = line[3:].split()[0]
                cur_data = {}
                continue
            if tag == " -3":                      # 区块结束
                if state == "result" and cur_kind:
                    blocks.append((mode_no, cur_kind, cur_data))
                cur_kind = None
                cur_data = {}
                state = "none"
                continue
            if tag != " -1":
                # 参数行：1PSTEP / 1PGM / 1PMODE / 100CL，字段位置随前缀空格变化，
                # 统一按空白切分处理，不用固定列宽。
                # 注意 1PSTEP 是「输出块序号」（10 阶 × 4 种结果 = 40），
                # 真正的模态号在 1PMODE，频率在 100CL 行的第 3 个字段。
                toks = line.split()
                if not toks:
                    continue
                key = toks[0]
                if key.endswith("1PMODE"):
                    mode_no = int(toks[1])
                elif key.endswith("100CL") and len(toks) > 2:
                    try:
                        freqs[mode_no] = float(toks[2])
                    except ValueError:
                        pass
                continue

            if state == "nodes":
                nid = int(line[3:13])
                coords[nid] = (float(line[13:25]), float(line[25:37]), float(line[37:49]))
                node_order.append(nid)
            elif state == "result" and cur_kind == "DISP":
                nid = int(line[3:13])
                cur_data[nid] = (float(line[13:25]), float(line[25:37]), float(line[37:49]))
    return node_order, coords, blocks, freqs


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    node_order, coords, blocks, freqs = parse_frd(FRD)
    print("nodes:", len(node_order), "blocks:", len(blocks), "steps:", len(freqs))

    disp_modes = {}
    for step, kind, data in blocks:
        if kind == "DISP" and step <= NMODES:
            disp_modes[step] = data

    ids = np.array(node_order, dtype=int)
    xyz = np.array([coords[i] for i in node_order], dtype=float)

    lines = ["mode,freq_Hz,node,x_mm,y_mm,z_mm,ux,uy,uz,umag"]
    for step in sorted(disp_modes):
        f = freqs.get(step, float("nan"))
        data = disp_modes[step]
        for nid, (ux, uy, uz) in data.items():
            x, y, z = coords[nid]
            um = (ux * ux + uy * uy + uz * uz) ** 0.5
            lines.append("%d,%.4f,%d,%.4f,%.4f,%.4f,%.6e,%.6e,%.6e,%.6e"
                         % (step, f, nid, x, y, z, ux, uy, uz, um))
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote", OUT_CSV, os.path.getsize(OUT_CSV), "bytes")

    # 每阶最大位移，确认振型已归一化
    for step in sorted(disp_modes):
        d = np.array(list(disp_modes[step].values()))
        print("mode %2d  f=%9.2f Hz  |u|max=%.6e  |uz|max=%.6e  uz/|u|=%.3f"
              % (step, freqs.get(step, 0), np.linalg.norm(d, axis=1).max(),
                 np.abs(d[:, 2]).max(),
                 np.abs(d[:, 2]).max() / max(np.linalg.norm(d, axis=1).max(), 1e-30)))


if __name__ == "__main__":
    main()
