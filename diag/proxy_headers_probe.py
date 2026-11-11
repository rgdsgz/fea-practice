"""Second opinion: fetch via GitHubPP proxy with python (OpenSSL), inspect response headers,
and fetch the catalog zip directly (no proxy) a few times to measure stability."""
import time
import urllib.request

PROXY = "http://127.0.0.1:30912"
URL = "https://addons.freecad.org/addon_catalog_cache.zip"
STATUS = "https://addons.freecad.org/status"

# 1) via proxy, capture headers
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
for url in (URL, STATUS):
    try:
        r = opener.open(url, timeout=30)
        print("VIA PROXY", url, "->", r.status, dict(r.headers))
    except urllib.error.HTTPError as e:
        print("VIA PROXY", url, "-> HTTP", e.code, dict(e.headers), e.read(300))
    except Exception as e:
        print("VIA PROXY", url, "-> FAIL", type(e).__name__, e)

# 2) direct, no proxy env
opener2 = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for i in range(3):
    t0 = time.time()
    try:
        r = opener2.open(URL, timeout=40)
        data = r.read()
        print(f"DIRECT try{i+1} {URL} -> {r.status} {len(data)} bytes {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"DIRECT try{i+1} FAIL", type(e).__name__, e, f"{time.time()-t0:.2f}s")
    t0 = time.time()
    try:
        r = opener2.open(STATUS, timeout=40)
        print(f"DIRECT try{i+1} {STATUS} -> {r.status} {r.read()!r} {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"DIRECT try{i+1} status FAIL", type(e).__name__, e, f"{time.time()-t0:.2f}s")
