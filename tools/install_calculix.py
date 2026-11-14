"""解压 CalculiX 2.23 (Windows) 并把 ccx_dynamic.exe 替换进 PrePoMax 的 Solver 目录。

用法：
    F:\\Python3.13.13\\python.exe "D:\\E\\Model\\tools\\install_calculix.py"
"""
import os
import shutil
import sys
import zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ZIP = os.path.join(TOOLS, "downloads", "calculix_2.23_4win.zip")
REF_DIR = os.path.join(TOOLS, "CalculiX-2.23")
SOLVER_DIR = os.path.join(TOOLS, "PrePoMax", "Solver")


def main():
    if not os.path.exists(ZIP):
        print("找不到", ZIP)
        return 1
    os.makedirs(REF_DIR, exist_ok=True)
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        print(f"压缩包内 {len(names)} 个条目：")
        for n in names[:20]:
            print("   ", n)
        z.extractall(REF_DIR)
    print(f"[OK] 解压到 {REF_DIR}")

    # 找到 ccx_dynamic.exe / ccx.exe 所在目录
    found = {}
    for root, _dirs, files in os.walk(REF_DIR):
        for f in files:
            if f.lower() in ("ccx_dynamic.exe", "ccx.exe", "ccx_static.exe"):
                found[f.lower()] = os.path.join(root, f)
    print("找到的求解器:", found)

    target = os.path.join(SOLVER_DIR, "ccx_dynamic.exe")
    if "ccx_dynamic.exe" in found and os.path.isdir(SOLVER_DIR):
        backup = os.path.join(SOLVER_DIR, "ccx_dynamic.exe.2.22.bak")
        if os.path.exists(target) and not os.path.exists(backup):
            shutil.copy2(target, backup)
            print(f"[backup] 原求解器 -> {backup}")
        shutil.copy2(found["ccx_dynamic.exe"], target)
        print(f"[OK] 替换 {target}")
    else:
        print("[WARN] 没找到 ccx_dynamic.exe 或 PrePoMax Solver 目录，跳过替换")

    print("\nPrePoMax Solver 目录现状:")
    for f in sorted(os.listdir(SOLVER_DIR)):
        p = os.path.join(SOLVER_DIR, f)
        if os.path.isfile(p):
            print(f"   {f:28s} {os.path.getsize(p):>14,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
