"""去重实现文件中相邻的重复 `@node_spec(...)` 装饰器（保留最后一个）。

当前仓库节点实现以 `plugins/nodes/` 为源，节点定义/发现/校验统一走 V2 AST 管线。
本脚本仅处理 V2 发现清单中的实现文件（自动排除 shared/helpers 与 __init__.py）。

用法：
  仅检查（默认，不改写文件，发现问题返回非零码）：
    python -X utf8 -m tools.dedupe_node_specs

  应用修复（会改写源码文件）：
    python -X utf8 -m tools.dedupe_node_specs --apply
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from engine.nodes.pipeline.discovery import discover_implementation_files

if __package__:
    from ._bootstrap import ensure_workspace_root_on_sys_path, get_workspace_root
else:
    from _bootstrap import ensure_workspace_root_on_sys_path, get_workspace_root

ensure_workspace_root_on_sys_path()


def process_file(path: Path, *, apply: bool) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    i = 0
    removed_lines = 0
    out: list[str] = []

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        # 非装饰器行，正常输出
        if not stripped.startswith("@node_spec("):
            out.append(line)
            i += 1
            continue

        # 进入一串连续的 @node_spec(...) 装饰器块，直到遇到下一条非空且非注释的行
        blocks: list[tuple[int, int]] = []  # (start_idx, end_idx_inclusive)
        while i < len(lines) and lines[i].lstrip().startswith("@node_spec("):
            start_idx = i
            # 解析当前装饰器块的结束位置：按括号配对
            depth = 0
            end_idx = i
            j = i
            while j < len(lines):
                segment = lines[j]
                # 简单括号计数（适用于本项目的装饰器格式）
                depth += segment.count('(')
                depth -= segment.count(')')
                end_idx = j
                j += 1
                if depth <= 0:
                    break
            blocks.append((start_idx, end_idx))
            i = end_idx + 1

        # 查看接下来是否紧跟着函数定义（顶级 def）
        k = i
        while k < len(lines) and lines[k].strip() == "":
            k += 1
        is_followed_by_def = (k < len(lines) and lines[k].startswith("def "))

        if is_followed_by_def and len(blocks) > 1:
            # 保留最后一个装饰器块，其余整块删除
            keep_start, keep_end = blocks[-1]
            # 输出之前的空白（如果有）
            for idx in range(keep_start, keep_end + 1):
                out.append(lines[idx])
            # 统计被删除的行数
            for (s, e) in blocks[:-1]:
                removed_lines += (e - s + 1)
        else:
            # 无需去重：按原样输出所有块
            for (s, e) in blocks:
                for idx in range(s, e + 1):
                    out.append(lines[idx])

    if removed_lines > 0 and apply:
        path.write_text("".join(out), encoding="utf-8")
    return removed_lines


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="去重相邻重复的 @node_spec 装饰器（以 V2 发现清单为扫描源）")
    parser.add_argument("--apply", action="store_true", help="应用修复（会改写源码文件）")
    args = parser.parse_args(list(argv) if argv is not None else None)

    workspace_root = get_workspace_root()
    target_files = sorted(discover_implementation_files(workspace_root))

    total_removed = 0
    for py_file in target_files:
        removed = process_file(py_file, apply=bool(args.apply))
        if removed:
            action = "fix" if bool(args.apply) else "would-fix"
            print(f"[{action}] {py_file} - removed {removed} duplicate decorator lines")
        total_removed += removed

    if total_removed > 0:
        if bool(args.apply):
            print(f"[DONE] removed total {total_removed} duplicate decorator lines")
            return 0
        print(f"[ERROR] found {total_removed} duplicate decorator lines (run with --apply to fix)")
        return 1

    print("[OK] no duplicate @node_spec decorator blocks found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


