"""修复可选库安装：用清华镜像下载 fatpack / meshio 并解压到 tools/python_libs。

用法：
    F:\\Python3.13.13\\python.exe "D:\\E\\项目\\tools\\fix_pylibs.py"
"""
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "python_libs")
WHEEL_DIR = os.path.join(HERE, "downloads", "wheels")
MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple/"
UA = {"User-Agent": "Mozilla/5.0"}
PKGS = ["fatpack", "meshio"]


def fetch(url, timeout=60, tries=3):
    last = None
    for _ in range(tries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=timeout
            ).read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2)
    raise last


def version_key(filename, pkg):
    m = re.search(rf"{pkg}-([0-9][^-]*)-", filename)
    if not m:
        return (0,)
    parts = re.split(r"[.+]", m.group(1))
    out = []
    for p in parts:
        p = re.sub(r"\D.*$", "", p)
        out.append(int(p) if p.isdigit() else 0)
    return tuple(out)


def main():
    os.makedirs(TARGET, exist_ok=True)
    os.makedirs(WHEEL_DIR, exist_ok=True)
    # 清掉之前装错的 meshio 1.7.6
    for d in os.listdir(TARGET):
        if d.lower().startswith("meshio") or d.lower().startswith("pipdated"):
            shutil.rmtree(os.path.join(TARGET, d), ignore_errors=True)

    for pkg in PKGS:
        try:
            index = MIRROR + pkg + "/"
            html = fetch(index).decode("utf-8", "replace")
            cands = []
            for h in re.findall(r'href="([^"]+\.whl[^"]*)"', html):
                full = urllib.parse.urljoin(index, h)
                fn = full.split("/")[-1].split("#")[0]
                if "py3-none-any" in fn or "cp313-win_amd64" in fn or "cp312-win_amd64" in fn:
                    cands.append((version_key(fn, pkg), full, fn))
            if not cands:
                print(f"[FAIL] {pkg}: 镜像上找不到纯 Python wheel")
                continue
            cands.sort()
            _v, url, filename = cands[-1]
            dest = os.path.join(WHEEL_DIR, filename)
            if not os.path.exists(dest):
                print(f"[get] {pkg}: {filename}")
                open(dest, "wb").write(fetch(url, timeout=120))
            with zipfile.ZipFile(dest) as z:
                z.extractall(TARGET)
            print(f"[ok] {pkg}: {filename}")
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {pkg}: {type(exc).__name__} {exc}")

    sys.path.insert(0, TARGET)
    for mod in ("fatpack", "rainflow", "meshio"):
        try:
            m = __import__(mod)
            print(f"  {mod}: {getattr(m, '__version__', 'ok')}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {mod}: FAIL {type(exc).__name__} {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
