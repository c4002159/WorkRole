#!/usr/bin/env python3
"""检查某个角色本次改动是否越权。

用法:
  python scripts/check_paths.py <analyst|product|dev|test|maintainer>            初版阶段
  python scripts/check_paths.py <analyst|product|dev|test|maintainer> --change   变更阶段(首次上线后)

在仓库根目录运行。检查工作区里所有改动(已暂存、未暂存、未跟踪)。
有越权改动时退出码为 1。
"""
import fnmatch
import subprocess
import sys

COMMON = ["docs/issues.md"]

# 所有角色都不得修改:规则与规范、归档记录、变更模板
DENY = [
    "AGENTS.md",
    "docs/rules/*",
    "docs/standards/*",
    "docs/changes/archive/*",
    "docs/changes/_template/*",
]

DEP_FILES = ["requirements*.txt", "pyproject.toml", "package.json", "package-lock.json"]
DEV_COMMON = ["src/*", "tests/unit/*", ".env.example"] + DEP_FILES

# 初版阶段:直接写 docs/00-04
ALLOWED_INITIAL = {
    "analyst": ["docs/00-baseline.md"],
    "product": [
        "docs/01-product.md",
        "docs/01a-competitor.md",
        "docs/prototypes/*",
    ],
    "dev": ["docs/02-tech.md", "docs/openapi.yaml"] + DEV_COMMON,
    "test": [
        "docs/03-test.md",
        "docs/04-release.md",
        "tests/acceptance/*",
        "reports/*",
    ],
    "maintainer": ["docs/proposals/*"],
}

# 变更阶段:基线文档不可改,只写变更文件夹里的增量
ALLOWED_CHANGE = {
    "analyst": [],
    "product": [
        "docs/changes/*/proposal.md",
        "docs/changes/*/01-delta.md",
        "docs/changes/*/prototypes/*",
    ],
    "dev": ["docs/changes/*/02-delta.md"] + DEV_COMMON,
    "test": [
        "docs/changes/*/03-delta.md",
        "tests/acceptance/*",
        "reports/*",
    ],
    "maintainer": ["docs/proposals/*"],
}


def changed_files():
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "status", "--porcelain", "-uall"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    files = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:  # 重命名:新旧路径都检查
            files.extend(path.split(" -> "))
        else:
            files.append(path)
    return [f.strip().strip('"').replace("\\", "/") for f in files]


def matches(path, patterns):
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def main():
    args = sys.argv[1:]
    change = "--change" in args
    args = [a for a in args if a != "--change"]
    table = ALLOWED_CHANGE if change else ALLOWED_INITIAL
    if len(args) != 1 or args[0] not in table:
        print(__doc__)
        return 2
    role = args[0]
    allowed = table[role] + COMMON
    files = changed_files()
    bad = [f for f in files if matches(f, DENY) or not matches(f, allowed)]
    mode = "变更阶段" if change else "初版阶段"
    if bad:
        print(f"[越权] 角色 {role}({mode})不应修改以下文件:")
        for f in bad:
            print("  -", f)
        return 1
    if role == "dev":
        deps = [f for f in files if matches(f, DEP_FILES)]
        if deps:
            print("[提示] 依赖文件有改动,请确认任务里明确要求新增依赖:")
            for f in deps:
                print("  -", f)
    print(f"[通过] 角色 {role}({mode})的改动都在权限范围内。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
