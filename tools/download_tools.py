"""Download the toolchain installers into the workspace (tools/downloads).

Run: F:\\Python3.13.13\\python.exe D:\\E\\Model\\tools\\download_tools.py
"""
import os
import ssl
import sys
import time
import urllib.request

DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DEST, exist_ok=True)

CTX = ssl._create_unverified_context()
UA = {"User-Agent": "Mozilla/5.0"}

TARGETS = [
    (
        "https://prepomax.fs.um.si/Files/Downloads/PrePoMax%20v3.0.0.zip",
        "PrePoMax-v3.0.0.zip",
        (200_999_611, None),
    ),
    (
        "http://www.dhondt.de/calculix_2.23_4win.zip",
        "calculix_2.23_4win.zip",
        (None, None),
    ),
]


def download(url, filename, expect_size):
    path = os.path.join(DEST, filename)
    if os.path.exists(path):
        size = os.path.getsize(path)
        if expect_size is None or size == expect_size:
            print(f"[skip] {filename} already present ({size:,} bytes)")
            return True
    tmp = path + ".part"
    t0 = time.time()
    last = t0
    last_bytes = 0
    done = 0
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120, context=CTX) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            print(f"[start] {filename}: {total/1048576:.1f} MB from {url}")
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    now = time.time()
                    if now - last >= 3:
                        speed = (done - last_bytes) / (now - last) / 1048576
                        pct = (done / total * 100) if total else 0
                        print(
                            f"  {done/1048576:8.1f}/{total/1048576:.1f} MB "
                            f"({pct:5.1f}%) {speed:6.2f} MB/s",
                            flush=True,
                        )
                        last, last_bytes = now, done
        os.replace(tmp, path)
        size = os.path.getsize(path)
        print(f"[done] {filename}: {size:,} bytes in {time.time()-t0:.1f}s")
        if expect_size is not None and size != expect_size:
            print(f"[WARN] size mismatch, expected {expect_size:,}")
            return False
        return True
    except Exception as exc:
        print(f"[FAIL] {filename}: {type(exc).__name__} {exc}")
        return False


ok = True
for url, name, expect in TARGETS:
    ok = download(url, name, expect[0]) and ok
    print("")
print("ALL OK" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
