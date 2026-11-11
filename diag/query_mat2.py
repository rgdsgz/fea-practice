import sqlite3

DB = r"D:\E\项目\tools\选材\materials.db"
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("SELECT * FROM materials WHERE name IN ('CalculiX-Steel','Steel-Generic')")
cols = [d[0] for d in cur.description]
for row in cur.fetchall():
    print("----")
    for c, v in zip(cols, row):
        print(f"  {c}: {v}")
