#!/usr/bin/env python3
"""检查某个角色的改动是否越权。

用法:
  python scripts/check_paths.py <角色> [--change] [--since <提交号>]

  角色:analyst | product | dev | test | maintainer
  --change   变更阶段(首次上线后):基线文档只读,只能写变更文件夹里的增量
  --since    检查自 <提交号> 以来的全部改动(含已提交的)。
             默认只检查工作区里未提交的改动(已暂存、未暂存、未跟踪)

建议用法:开工前记下提交号 (git rev-parse HEAD),收工后
  python scripts/check_paths.py dev --since <提交号>

在仓库根目录运行。有越权改动时退出码为 1。
局限:只能判断"改了哪些文件",判断不了改得对不对,也区分不了改动是谁产生的。
每个角色请在各自独立的工作副本或独立的时间段里工作。
"""
import fnmatch
import subprocess
import sys

# 除维护角色外,所有角色都可以新增问题单
COMMON = ["docs/issues.md"]

# 所有角色都不得修改:规则与规范、归档记录、变更模板
DENY = [
    "AGENTS.md",
    "docs/rules/*",
    "docs/standards/*",
    "docs/changes/archive/*",
    "docs/changes/_template/*",
]

# 根目录的依赖与配置文件白名单(开发角色可写)。新增依赖需任务依据,脚本无法判断,只会提示
DEP_FILES = [
    "requirements*.txt", "pyproject.toml", "package.json", "package-lock.json",
    "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "Pipfile", "Pipfile.lock",
]
CONFIG_FILES = [
    ".env.example", "tsconfig*.json", "ruff.toml", ".eslintrc*", "eslint.config.*",
    ".prettierrc*", "pytest.ini", "setup.cfg", "tox.ini", "Makefile",
    "Dockerfile", "docker-compose*.yml", "docker-compose*.yaml",
]
DEV_COMMON = ["src/*", "tests/unit/*"] + DEP_FILES + CONFIG_FILES

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


def run_git(args):
    return subprocess.run(
        ["git", "-c", "core.quotepath=false"] + args,
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout


def clean(path):
    return path.strip().strip('"').replace("\\", "/")


def changed_files(since=None):
    files = set()
    if since:
        # 工作区相对 since 的全部差异(含已提交);--no-renames 让重命名的新旧路径都列出
        for line in run_git(["diff", "--name-only", "--no-renames", since]).splitlines():
            files.add(clean(line))
        # 未跟踪的新文件
        for line in run_git(["ls-files", "--others", "--exclude-standard"]).splitlines():
            files.add(clean(line))
    else:
        for line in run_git(["status", "--porcelain", "-uall"]).splitlines():
            if len(line) < 4:
                continue
            path = line[3:]
            if " -> " in path:  # 重命名:新旧路径都检查
                files.update(clean(p) for p in path.split(" -> "))
            else:
                files.add(clean(path))
    return sorted(f for f in files if f)


def matches(path, patterns):
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def parse_args(argv):
    change = False
    since = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--change":
            change = True
        elif a == "--since":
            if i + 1 >= len(argv):
                return None
            since = argv[i + 1]
            i += 1
        else:
            rest.append(a)
        i += 1
    return change, since, rest


def main():
    parsed = parse_args(sys.argv[1:])
    if parsed is None:
        print(__doc__)
        return 2
    change, since, rest = parsed
    table = ALLOWED_CHANGE if change else ALLOWED_INITIAL
    if len(rest) != 1 or rest[0] not in table:
        print(__doc__)
        return 2
    role = rest[0]
    allowed = list(table[role])
    if role != "maintainer":
        allowed += COMMON
    try:
        files = changed_files(since)
    except subprocess.CalledProcessError as e:
        print("git 命令失败:", (e.stderr or "").strip() or e)
        return 2
    bad = [f for f in files if matches(f, DENY) or not matches(f, allowed)]
    mode = "变更阶段" if change else "初版阶段"
    scope = f"自 {since} 以来" if since else "工作区未提交"
    if bad:
        print(f"[越权] 角色 {role}({mode},{scope})不应修改以下文件:")
        for f in bad:
            print("  -", f)
        return 1
    if role == "dev":
        deps = [f for f in files if matches(f, DEP_FILES)]
        if deps:
            print("[提示] 依赖文件有改动,请确认任务里明确要求新增依赖:")
            for f in deps:
                print("  -", f)
    print(f"[通过] 角色 {role}({mode},{scope})的改动都在权限范围内。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
