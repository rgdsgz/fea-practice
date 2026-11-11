"""把 PrePoMax 绿色版解压到 tools/PrePoMax（去掉压缩包内的版本号目录，路径更短）。

用法：
    F:\\Python3.13.13\\python.exe "D:\\E\\项目\\tools\\install_prepomax.py"
"""
import os
import shutil
import sys
import zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ZIP = os.path.join(TOOLS, "downloads", "PrePoMax-v3.0.0.zip")
TARGET = os.path.join(TOOLS, "PrePoMax")


def main():
    if not os.path.exists(ZIP):
        print("找不到", ZIP)
        return 1
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        top = names[0].split("/")[0] + "/"
        if os.path.isdir(TARGET):
            shutil.rmtree(TARGET)
        os.makedirs(TARGET, exist_ok=True)
        n = 0
        for info in z.infolist():
            if not info.filename.startswith(top):
                continue
            rel = info.filename[len(top):]
            if not rel:
                continue
            dest = os.path.join(TARGET, rel.replace("/", os.sep))
            if info.is_dir():
                os.makedirs(dest, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
            n += 1
    print(f"[OK] 解压 {n} 个文件到 {TARGET}")
    exe = os.path.join(TARGET, "PrePoMax.exe")
    print("主程序:", exe, "存在" if os.path.exists(exe) else "缺失!")
    solver = os.path.join(TARGET, "Solver")
    if os.path.isdir(solver):
        print("内置求解器:")
        for f in sorted(os.listdir(solver)):
            p = os.path.join(solver, f)
            print(f"   {f:20s} {os.path.getsize(p):>12,} bytes" if os.path.isfile(p) else f"   {f}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
