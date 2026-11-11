"""把纯 Python 依赖的 wheel 直接解压到 tools/python_libs（绕开 pip 在受限环境下的临时目录问题）。

用法：
    F:\\Python3.13.13\\python.exe "D:\\E\\项目\\tools\\install_pylibs.py"

安装：fatpack（疲劳 S-N/雨流）、rainflow（雨流计数）、meshio（网格/结果格式转换）。
装好后把 tools/python_libs 加入 sys.path 即可 import（脚本里已自动处理）。
"""
import os
import re
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "python_libs")
WHEEL_DIR = os.path.join(HERE, "downloads", "wheels")
UA = {"User-Agent": "Mozilla/5.0"}
PKGS = ["fatpack", "rainflow", "meshio"]


def fetch(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def pick_wheel(pkg):
    index = f"https://pypi.org/simple/{pkg}/"
    html = fetch(index).decode("utf-8", "replace")
    hrefs = re.findall(r'href="([^"]+\.whl[^"]*)"', html)
    candidates = []
    for h in hrefs:
        full = urllib.parse.urljoin(index, h)
        filename = full.split("/")[-1].split("#")[0]
        candidates.append((full, filename))
    # 优先级：py3-none-any（纯 Python）> cp3xx-win_amd64 > 其它
    for pattern in (r"py3-none-any\.whl$", r"cp3\d+-abi3-win_amd64\.whl$", r"cp3\d+-win_amd64\.whl$"):
        for full, filename in candidates:
            if re.search(pattern, filename):
                return full, filename
    return candidates[-1] if candidates else (None, None)


def main():
    os.makedirs(TARGET, exist_ok=True)
    os.makedirs(WHEEL_DIR, exist_ok=True)
    ok = True
    for pkg in PKGS:
        try:
            url, name = pick_wheel(pkg)
            if not url:
                print(f"[FAIL] {pkg}: 找不到 wheel")
                ok = False
                continue
            dest = os.path.join(WHEEL_DIR, name)
            if not os.path.exists(dest):
                print(f"[get] {pkg}: {name}")
                open(dest, "wb").write(fetch(url, timeout=120))
            with zipfile.ZipFile(dest) as z:
                z.extractall(TARGET)
            print(f"[ok] {pkg}: 解压 {name} -> {TARGET}")
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {pkg}: {type(exc).__name__} {exc}")
            ok = False
    print("\n测试导入（通过 tools/python_libs）:")
    sys.path.insert(0, TARGET)
    for mod in ("fatpack", "rainflow", "meshio"):
        try:
            m = __import__(mod)
            print(f"  {mod}: {getattr(m, '__version__', 'import ok')}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {mod}: FAIL {type(exc).__name__} {exc}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
