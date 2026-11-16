"""新建一个建模/FEA 项目目录（复制 项目\\_模板 的结构）。

用法：
    F:\\Python3.13.13\\python.exe D:\\E\\Model\\tools\\new_project.py 001-支架强度校核
    # 项目已存在时只补缺失目录、覆盖 README：
    ... new_project.py 001-支架强度校核 --force

生成的目录：
    项目\\<name>\\
        01-几何\\   02-网格\\   03-计算\\   04-结果\\   05-报告\\
        README.md（由模板填入项目名和日期）
"""
import argparse
import datetime
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(ROOT, "项目", "_模板")
PROJECTS_DIR = os.path.join(ROOT, "项目")
SUBDIRS = ["01-几何", "02-网格", "03-计算", "04-结果", "05-报告"]
BAD_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]')


def main() -> int:
    ap = argparse.ArgumentParser(description="新建建模/FEA 项目目录")
    ap.add_argument("name", help="项目目录名，如 001-支架强度校核")
    ap.add_argument("--force", action="store_true",
                    help="目录已存在时也继续（补建缺失子目录、覆盖 README）")
    args = ap.parse_args()

    name = args.name.strip().strip("\\/")
    if not name:
        print("[错误] 项目名不能为空", file=sys.stderr)
        return 2
    if BAD_CHARS.search(name):
        print(f'[错误] 项目名不能包含 \\ / : * ? " < > | 等字符：{name}', file=sys.stderr)
        return 2

    dest = os.path.join(PROJECTS_DIR, name)
    if os.path.exists(dest) and not args.force:
        print(f"[错误] 项目已存在：{dest}\n       如需补建/覆盖 README，加 --force", file=sys.stderr)
        return 2

    for sub in SUBDIRS:
        os.makedirs(os.path.join(dest, sub), exist_ok=True)

    # R3（AGENTS.md §3.1）：预先建好纯 ASCII 的 FEM 网格工作目录，中文路径会让 Gmsh 报
    # `Unable to open file`。这里只建目录，偏好键需在 FreeCAD 控制台里设（见输出提示与模板 README）。
    m = re.match(r"\s*(\d+)", name)
    fem_dir = os.path.join(ROOT, f"fem{m.group(1)}" if m else f"fem_{name}")
    try:
        os.makedirs(fem_dir, exist_ok=True)
    except OSError as exc:
        print(f"[警告] 无法创建 FEM 工作目录 {fem_dir}：{exc}", file=sys.stderr)

    # 由模板生成 README
    tpl_path = os.path.join(TEMPLATE_DIR, "README.md")
    readme_path = os.path.join(dest, "README.md")
    if os.path.exists(tpl_path):
        with open(tpl_path, encoding="utf-8") as f:
            text = f.read()
        today = datetime.date.today().isoformat()
        text = text.replace("{{项目名称}}", name).replace("{{日期}}", today)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(f"[警告] 找不到模板 {tpl_path}，跳过 README", file=sys.stderr)

    print(f"[OK] 项目已创建：{dest}")
    for sub in SUBDIRS:
        print(f"     {sub}\\")
    print("\n下一步：")
    print("  0. 【必做】把 FEM 网格工作目录设成纯 ASCII 路径（AGENTS.md R3 / §3.1）。")
    print("     中文路径会让 Gmsh 报 `Unable to open file`，网格永远生成不出来。")
    print("     在 FreeCAD 的 Python 控制台执行：")
    print("       import os, FreeCAD")
    print(f"       os.makedirs(r'{fem_dir}', exist_ok=True)")
    print("       p = FreeCAD.ParamGet(\"User parameter:BaseApp/Preferences/Mod/Fem/General\")")
    print("       p.SetBool(\"UseCustomDirectory\", 1); p.SetBool(\"UseTempDirectory\", 0)")
    print(f"       p.SetString(\"CustomDirectoryPath\", r'{fem_dir}')")
    print("       FreeCAD.saveParameter()")
    print(f"  1. 建模 → 文件放 {dest}\\01-几何（几何对象内部 Name 用 ASCII）")
    print(f"  2. 网格 → 文件放 {dest}\\02-网格")
    print("  3. 求解（PrePoMax GUI 或 ccx 命令行）")
    print(f"  4. 结果 → {dest}\\04-结果，填写 {readme_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
