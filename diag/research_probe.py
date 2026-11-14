"""Research probe: GitHub repo metadata + FreeCAD addon catalog scan + download reachability.

Run with: F:\\Python3.13.13\\python.exe D:\\E\\Model\\diag\\research_probe.py
"""
import io
import json
import sys
import time
import urllib.request
import zipfile

UA = {"User-Agent": "Mozilla/5.0 (research-probe)"}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout)


REPOS = [
    "FreeCAD/FreeCAD",
    "FreeCAD/Addons",
    "FreeCAD/FreeCAD-documentation",
    "ElmerCSC/elmerfem",
    "FEniCS/dolfinx",
    "mfem/mfem",
    "nschloe/meshio",
    "nschloe/pygmsh",
    "hackingmaterials/matminer",
    "materialsproject/pymatgen",
    "DISOGitHub/FastCAE",
    "SalomePlatform/salome",
]

print("===== GitHub repo metadata =====")
for repo in REPOS:
    try:
        info = json.load(get(f"https://api.github.com/repos/{repo}"))
        lic = (info.get("license") or {}).get("spdx_id")
        stars = info.get("stargazers_count")
        pushed = (info.get("pushed_at") or "")[:10]
        rel = ""
        try:
            r = json.load(get(f"https://api.github.com/repos/{repo}/releases/latest"))
            rel = f"{r.get('tag_name')} @ {(r.get('published_at') or '')[:10]}"
        except Exception:
            rel = "no release"
        print(f"{repo}: stars={stars} license={lic} pushed={pushed} latest={rel}")
    except Exception as exc:
        print(f"{repo}: FAIL {type(exc).__name__} {exc}")
    time.sleep(0.3)

print()
print("===== FreeCAD addon catalog: FEM/CFD/mesh/material-related addons =====")
try:
    data = get("https://addons.freecad.org/addon_catalog_cache.zip", timeout=120).read()
    print("catalog zip bytes:", len(data))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        print("zip entries:", z.namelist())
        name = z.namelist()[0]
        catalog = json.loads(z.read(name))
    print("top-level keys:", list(catalog.keys())[:5])
    keywords = ("fem", "cfd", "mesh", "meshing", "material", "simulation", "simulat",
                "calculix", "gmsh", "openfoam", "topology", "optimiz", "optimis", "solver")
    n = 0
    for addon_id, entries in catalog.items():
        if addon_id.startswith("_") or addon_id.startswith("$"):
            continue
        if not entries:
            continue
        e = entries[0]
        desc = (e.get("description") or "")
        display = (e.get("display_name") or "")
        text = (addon_id + " " + display + " " + desc).lower()
        if any(k in text for k in keywords):
            n += 1
            repo = ""
            for k in ("repository", "git_ref", "zip_url"):
                if e.get(k):
                    repo = e[k]
                    break
            print(f"- {addon_id} | {display} | {repo} | {desc[:110]}")
    print("matched addons:", n)
except Exception as exc:
    print("catalog FAIL", type(exc).__name__, exc)

print()
print("===== download site reachability =====")
SITES = [
    "https://dev.opencascade.org/",
    "https://www.gmsh.info/",
    "https://gmsh.info/",
    "https://www.dhondt.de/",
    "https://prepomax.fs.um.si/",
    "https://prepomax.fs.um.si/downloads/",
    "https://www.code-aster.org/",
    "https://www.salome-platform.org/",
    "https://www.csc.fi/en/web/elmer",
    "https://z88.uni-bayreuth.de/",
    "https://www.simscale.com/",
    "https://materialsproject.org/",
    "https://matweb.com/",
    "https://www.engineeringtoolbox.com/",
    "https://www.ansys.com/academic/students",
    "https://www.freecad.org/",
    "https://forum.freecad.org/",
    "https://www.mecway.com/",
]
for site in SITES:
    t0 = time.time()
    try:
        r = get(site, timeout=20)
        print(f"{site} -> {r.status} {(time.time()-t0):.1f}s")
    except Exception as exc:
        print(f"{site} -> FAIL {type(exc).__name__} {str(exc)[:80]} {(time.time()-t0):.1f}s")
