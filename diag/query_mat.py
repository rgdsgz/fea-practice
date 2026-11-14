import sqlite3

DB = r"D:\E\Model\tools\选材\materials.db"
con = sqlite3.connect(DB)
cur = con.cursor()
print("columns:", [r[1] for r in cur.execute("PRAGMA table_info(materials)")])
rows = cur.execute(
    "SELECT name, category, E_GPa, nu, yield_MPa, uts_MPa, density_kg_m3 "
    "FROM materials WHERE name LIKE '%Steel%' OR name LIKE '%Q235%' "
    "ORDER BY name"
).fetchall()
for r in rows:
    print(r)
