"""为 SheetMetal 安装 networkx 依赖到 FreeCAD 的 AdditionalPythonPackages/py311。

FreeCAD 启动时会把该目录加入 sys.path（已实测），因此补上 networkx 即可。

用法：
    F:\\Python3.13.13\\python.exe "D:\\E\\项目\\tools\\install_sheetmetal_dep.py"
"""
import os
import shutil
import sys
import urllib.request
import zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(TOOLS, "downloads", "addons")
TARGET = os.path.join(
    os.environ["APPDATA"], "FreeCAD", "v1-1", "AdditionalPythonPackages", "py311"
)
URL = "https://codeload.github.com/networkx/networkx/zip/refs/tags/networkx-3.5"
UA = {"User-Agent": "Mozilla/5.0"}


def main():
    os.makedirs(TARGET, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    zip_path = os.path.join(CACHE, "networkx.zip")
    if not (os.path.exists(zip_path) and os.path.getsize(zip_path) > 0):
        print("[get]", URL)
        with urllib.request.urlopen(
            urllib.request.Request(URL, headers=UA), timeout=120
        ) as r, open(zip_path + ".part", "wb") as f:
            while True:
                chunk = r.read(1024 * 512)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(zip_path + ".part", zip_path)
    print(f"[ok] {zip_path} ({os.path.getsize(zip_path):,} bytes)")

    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        top = names[0].split("/")[0] + "/"
        prefix = top + "networkx/"
        pkg_target = os.path.join(TARGET, "networkx")
        if os.path.isdir(pkg_target):
            shutil.rmtree(pkg_target)
        count = 0
        for info in z.infolist():
            if not info.filename.startswith(prefix):
                continue
            rel = info.filename[len(prefix):]
            if not rel:
                continue
            dest = os.path.join(pkg_target, rel.replace("/", os.sep))
            if info.is_dir():
                os.makedirs(dest, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    print(f"[install] networkx: {count} 个文件 -> {pkg_target}")

    for junk in ("dsh_probe.py", "__pycache__"):
        p = os.path.join(TARGET, junk)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p):
            os.remove(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
