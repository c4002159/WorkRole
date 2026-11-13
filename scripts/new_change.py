#!/usr/bin/env python3
"""创建一个新的变更文件夹。

用法:  python scripts/new_change.py <名称>
例:    python scripts/new_change.py 增加日环比

在仓库根目录运行。编号自动延续(包含 archive 里已有的)。
"""
import datetime
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHANGES = ROOT / "docs" / "changes"
TEMPLATE = CHANGES / "_template"


def next_number():
    nums = []
    for base in (CHANGES, CHANGES / "archive"):
        if not base.exists():
            continue
        for p in base.iterdir():
            m = re.match(r"(?:\d{4}-\d{2}-\d{2}-)?CHG-(\d+)", p.name)
            if p.is_dir() and m:
                nums.append(int(m.group(1)))
    return max(nums, default=0) + 1


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    name = re.sub(r'[\\/:*?"<>|\s]+', "-", sys.argv[1].strip())
    if not name:
        print("名称不能为空")
        return 2
    if not TEMPLATE.exists():
        print(f"找不到模板目录: {TEMPLATE}")
        return 1
    chg_id = f"CHG-{next_number():03d}"
    target = CHANGES / f"{chg_id}-{name}"
    if target.exists():
        print(f"已存在: {target}")
        return 1
    shutil.copytree(TEMPLATE, target)
    today = datetime.date.today().isoformat()
    for f in target.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        text = text.replace("CHG-XXX 名称", f"{chg_id} {name}").replace("YYYY-MM-DD", today)
        f.write_text(text, encoding="utf-8")
    print(f"已创建 {target.relative_to(ROOT)}")
    print("下一步:在 docs/issues.md 登记一条类型为'变更请求'的问题,再用 README 里的消息模板启动产品 agent。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
