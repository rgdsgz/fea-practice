"""从 FreeCAD 自带的 .FCMat 材料卡构建本地选材数据库 (SQLite + CSV)。

用法（用 FreeCAD 自带 Python，因为它带 PyYAML/pandas）：
    F:\\FreeCAD\\bin\\python.exe "D:\\E\\项目\\tools\\选材\\build_materials.py"

输出：
    D:\\E\\项目\\tools\\选材\\materials.db    （SQLite，表 materials）
    D:\\E\\项目\\tools\\选材\\materials.csv   （Excel 可直接打开）

数据库字段说明见 README 或表结构注释。疲劳字段（sigma_f / b / Se）默认留空，
由使用者按实测 S-N 数据或工程估算填写。
"""
import csv
import glob
import os
import re
import sqlite3
import sys

import yaml

FREECAD_MATERIALS = r"F:\FreeCAD\data\Mod\Material\Resources\Materials\Standard"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(OUT_DIR, "materials.db")
CSV_PATH = os.path.join(OUT_DIR, "materials.csv")

LEN_PREFIX = {"": 1.0, "k": 1e3, "M": 1e6, "G": 1e9, "m": 1e-3, "µ": 1e-6, "u": 1e-6, "n": 1e-9}

QTY_RE = re.compile(r"^\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*(.*?)\s*$")


def parse_qty(text):
    """'140.0 GPa' -> (140.0, 'GPa')"""
    if text is None:
        return None, None
    if isinstance(text, (int, float)):
        return float(text), ""
    m = QTY_RE.match(str(text))
    if not m:
        return None, None
    try:
        return float(m.group(1)), m.group(2)
    except ValueError:
        return None, None


def to_pa(text):
    """压力/模量统一转 Pa"""
    val, unit = parse_qty(text)
    if val is None:
        return None
    unit = unit.replace(" ", "").replace("^", "")
    if unit in ("Pa",):
        return val
    if unit in ("kPa",):
        return val * 1e3
    if unit in ("MPa", "N/mm2", "N/mm²"):
        return val * 1e6
    if unit in ("GPa",):
        return val * 1e9
    if unit in ("psi",):
        return val * 6894.757
    if unit in ("ksi",):
        return val * 6.894757e6
    if unit in ("bar",):
        return val * 1e5
    return None


def to_gpa(text):
    pa = to_pa(text)
    return None if pa is None else pa / 1e9


def to_mpa(text):
    pa = to_pa(text)
    return None if pa is None else pa / 1e6


def to_density(text):
    """kg/m^3"""
    val, unit = parse_qty(text)
    if val is None:
        return None
    unit = unit.replace(" ", "").replace("^", "")
    if unit in ("kg/m3", "kg/m³"):
        return val
    if unit in ("g/cm3", "g/cm³"):
        return val * 1000.0
    if unit in ("t/m3",):
        return val * 1000.0
    if unit in ("lb/ft3",):
        return val * 16.0185
    return None


def to_expansion(text):
    """1/K"""
    val, unit = parse_qty(text)
    if val is None:
        return None
    unit = unit.replace(" ", "").replace("^", "")
    if unit in ("µm/m/K", "um/m/K", "μm/m/K"):
        return val * 1e-6
    if unit in ("m/m/K", "1/K", "1/°C", "1/degC"):
        return val
    if unit in ("mm/mm/K",):
        return val * 1e-3
    return None


def to_conductivity(text):
    """W/m/K"""
    val, unit = parse_qty(text)
    if val is None:
        return None
    unit = unit.replace(" ", "").replace("^", "")
    if unit in ("W/m/K", "W/mK"):
        return val
    return None


def first_model(models, candidates):
    for key in candidates:
        if key in models:
            return models[key]
    return {}


def build_rows():
    rows = []
    files = glob.glob(os.path.join(FREECAD_MATERIALS, "**", "*.FCMat"), recursive=True)
    for path in files:
        try:
            data = yaml.safe_load(open(path, encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] YAML 解析失败 {path}: {exc}")
            continue
        general = data.get("General", {}) or {}
        models = data.get("Models", {}) or {}
        le = first_model(
            models,
            ["LinearElastic", "IsotropicLinearElastic", "Linear Elastic", "LinearElasticity"],
        )
        thermal = models.get("Thermal", {}) or {}
        std = models.get("MaterialStandard", {}) or {}
        costs = models.get("Costs", {}) or {}
        rel = os.path.relpath(path, FREECAD_MATERIALS)
        parts = rel.split(os.sep)
        category = parts[0] if len(parts) > 1 else "Standard"
        subcategory = "/".join(parts[1:-1]) if len(parts) > 2 else ""

        name = general.get("Name") or os.path.splitext(parts[-1])[0]
        rows.append(
            {
                "name": name,
                "category": category,
                "subcategory": subcategory,
                "kind": std.get("KindOfMaterial") or "",
                "density_kg_m3": to_density(le.get("Density")),
                "E_GPa": to_gpa(le.get("YoungsModulus")),
                "nu": (lambda v: v[0] if v[0] is not None else None)(
                    parse_qty(le.get("PoissonRatio"))
                ),
                "yield_MPa": to_mpa(le.get("YieldStrength")),
                "uts_MPa": to_mpa(le.get("UltimateTensileStrength")),
                "shear_GPa": to_gpa(le.get("ShearModulus")),
                "elongation_pct": (lambda v: v[0] if v[0] is not None else None)(
                    parse_qty(le.get("UltimateStrain"))
                ),
                "cte_1_K": to_expansion(thermal.get("ThermalExpansionCoefficient")),
                "k_W_mK": to_conductivity(thermal.get("ThermalConductivity")),
                "cost": (lambda v: str(v) if v is not None else "")(
                    costs.get("Cost") or costs.get("EstimatedCost") or None
                ),
                "sigma_f_MPa": None,
                "b": None,
                "Se_MPa": None,
                "source": "FreeCAD bundled material card (.FCMat)",
                "source_file": rel,
            }
        )
    return rows


def main():
    rows = build_rows()
    if not rows:
        print("没有找到任何材料卡，检查", FREECAD_MATERIALS)
        return 1
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            subcategory TEXT,
            kind TEXT,
            density_kg_m3 REAL,
            E_GPa REAL,
            nu REAL,
            yield_MPa REAL,
            uts_MPa REAL,
            shear_GPa REAL,
            elongation_pct REAL,
            cte_1_K REAL,
            k_W_mK REAL,
            cost TEXT,
            sigma_f_MPa REAL,   -- 疲劳: Basquin 疲劳强度系数（MPa），可留空
            b REAL,             -- 疲劳: Basquin 疲劳强度指数，可留空
            Se_MPa REAL,        -- 疲劳: 耐久极限（MPa），可留空
            source TEXT,
            source_file TEXT,
            UNIQUE(name, source_file)
        )
        """
    )
    cur.executemany(
        """
        INSERT OR REPLACE INTO materials
        (name, category, subcategory, kind, density_kg_m3, E_GPa, nu, yield_MPa, uts_MPa,
         shear_GPa, elongation_pct, cte_1_K, k_W_mK, cost, sigma_f_MPa, b, Se_MPa,
         source, source_file)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                r["name"], r["category"], r["subcategory"], r["kind"], r["density_kg_m3"],
                r["E_GPa"], r["nu"], r["yield_MPa"], r["uts_MPa"], r["shear_GPa"],
                r["elongation_pct"], r["cte_1_K"], r["k_W_mK"], r["cost"],
                r["sigma_f_MPa"], r["b"], r["Se_MPa"], r["source"], r["source_file"],
            )
            for r in rows
        ],
    )
    conn.commit()

    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    conn.close()

    n_metal = sum(1 for r in rows if r["category"] == "Metal")
    n_thermoplast = sum(1 for r in rows if r["category"] == "Thermoplast")
    print(f"[OK] 写入 {len(rows)} 条材料（金属 {n_metal}，热塑性塑料 {n_thermoplast}）")
    print("   数据库:", DB_PATH)
    print("   CSV   :", CSV_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
