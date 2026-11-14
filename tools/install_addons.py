"""安装 FreeCAD 插件（fasteners / sheetmetal / Supplemental-Materials）到用户 Mod 目录。

下载 zip 后解压（去掉压缩包顶层目录）到：
    %APPDATA%\\FreeCAD\\v1-1\\Mod\\<AddonName>

用法：
    F:\\Python3.13.13\\python.exe "D:\\E\\Model\\tools\\install_addons.py"
"""
import os
import shutil
import sys
import urllib.request
import zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(TOOLS, "downloads", "addons")
MOD = os.path.join(os.environ["APPDATA"], "FreeCAD", "v1-1", "Mod")
UA = {"User-Agent": "Mozilla/5.0"}

ADDONS = [
    (
        "Fasteners",
        "codeload://shaise/FreeCAD_FastenersWB/zip/refs/heads/master",
    ),
    (
        "SheetMetal",
        "codeload://shaise/FreeCAD_SheetMetal/zip/refs/heads/master",
    ),
    (
        "Supplemental-Materials",
        "codeload://FreeCAD/Supplemental-Materials/zip/refs/heads/Latest",
    ),
]

PROXY = "http://127.0.0.1:30912"
REQUIRED = ("package.xml", "InitGui.py", "Init.py")


def _open(url, proxy=None, timeout=90):
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
        req = urllib.request.Request(url, headers=UA)
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)


def download(url, filename, tries=2):
    path = os.path.join(CACHE, filename)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"[skip] 已缓存 {filename} ({os.path.getsize(path):,} bytes)")
        return path
    if url.startswith("codeload://"):
        url = "https://codeload.github.com/" + url[len("codeload://"):]
    for attempt in range(1, tries + 1):
        for proxy in (None, PROXY) if attempt > 1 else (None,):
            mode = f"proxy {proxy}" if proxy else "direct"
            print(f"[get] {filename} ({mode})")
            try:
                with _open(url, proxy) as r, open(path + ".part", "wb") as f:
                    while True:
                        chunk = r.read(1024 * 512)
                        if not chunk:
                            break
                        f.write(chunk)
                os.replace(path + ".part", path)
                print(f"[ok] {filename} ({os.path.getsize(path):,} bytes)")
                return path
            except Exception as exc:  # noqa: BLE001
                print(f"   失败: {type(exc).__name__} {str(exc)[:80]}")
    raise RuntimeError(f"下载失败: {url}")


def install(folder, zip_path):
    target = os.path.join(MOD, folder)
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        top = names[0].split("/")[0] + "/"
        if os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(target, exist_ok=True)
        count = 0
        for info in z.infolist():
            if not info.filename.startswith(top):
                continue
            rel = info.filename[len(top):]
            if not rel:
                continue
            dest = os.path.join(target, rel.replace("/", os.sep))
            if info.is_dir():
                os.makedirs(dest, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    present = [f for f in REQUIRED if os.path.exists(os.path.join(target, f))]
    print(f"[install] {folder}: {count} 个文件, 关键文件: {present or '缺失!'} -> {target}")
    return len(present) > 0


def main():
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(MOD, exist_ok=True)
    ok = True
    for folder, url in ADDONS:
        try:
            zp = download(url, folder + ".zip")
            ok = install(folder, zp) and ok
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {folder}: {type(exc).__name__} {exc}")
            ok = False
    print("\n=== Mod 目录现状 ===")
    for d in sorted(os.listdir(MOD)):
        p = os.path.join(MOD, d)
        if os.path.isdir(p):
            files = sum(len(fs) for _r, _d, fs in os.walk(p))
            print(f"  {d:26s} {files:>5} files")
    print("\n完成" if ok else "\n部分失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
