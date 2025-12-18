"""
检测 `engine/configs` 目录下的重复类名。

当前仓库以 `engine/configs` 作为唯一配置模型来源。
本脚本扫描目标目录下的 Python 文件，找出跨模块的同名类定义（可能导致导入歧义或认知冲突）。

用法（推荐）：
  python -X utf8 -m tools.check_duplicate_config_names
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Sequence
import argparse

# 允许 `python tools/check_duplicate_config_names.py` 与 `python -m tools.check_duplicate_config_names`
if __package__:
    from ._bootstrap import ensure_workspace_root_on_sys_path, get_workspace_root
else:
    from _bootstrap import ensure_workspace_root_on_sys_path, get_workspace_root

ensure_workspace_root_on_sys_path()

# 需要忽略的文件
IGNORE_FILES = {
    "__init__.py",  # 导出文件
    "__pycache__",
}

# 需要忽略的类名（已知的合理重复或向后兼容别名）
IGNORE_CLASS_NAMES = {
    "BaseModel",  # pydantic基类
    "Enum",  # 枚举基类
}


def extract_class_definitions(file_path: Path) -> List[Tuple[str, int]]:
    """
    从Python文件中提取所有类定义
    
    返回：[(类名, 行号), ...]
    """
    class_definitions = []
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_number, line in enumerate(file, start=1):
            # 匹配类定义：class ClassName 或 class ClassName(BaseClass)
            match = re.match(r'^class\s+(\w+)', line)
            if match:
                class_name = match.group(1)
                if class_name not in IGNORE_CLASS_NAMES:
                    class_definitions.append((class_name, line_number))
    
    return class_definitions


def scan_config_directory(project_root: Path, config_dir: Path) -> Dict[str, List[Tuple[str, int]]]:
    """
    扫描配置目录，收集所有类定义
    
    返回：{文件路径: [(类名, 行号), ...]}
    """
    file_classes = {}
    
    if not config_dir.exists():
        raise SystemExit(f"[ERROR] 目标目录不存在：{config_dir}（请确认仓库结构或使用 --config-dir 指定）")

    for file_path in config_dir.rglob("*.py"):
        if file_path.name in IGNORE_FILES:
            continue
        # 忽略 __pycache__ 子目录
        if "__pycache__" in file_path.parts:
            continue
        classes = extract_class_definitions(file_path)
        if classes:
            rel_path = file_path.relative_to(project_root)
            file_classes[str(rel_path)] = classes
    
    return file_classes


def find_duplicate_classes(file_classes: Dict[str, List[Tuple[str, int]]]) -> Dict[str, List[Tuple[str, int]]]:
    """
    找出重复的类名
    
    返回：{类名: [(文件路径, 行号), ...]}
    """
    class_locations = defaultdict(list)
    
    for file_path, classes in file_classes.items():
        for class_name, line_number in classes:
            class_locations[class_name].append((file_path, line_number))
    
    # 筛选出出现多次的类名
    duplicates = {
        class_name: locations
        for class_name, locations in class_locations.items()
        if len(locations) > 1
    }
    
    return duplicates


def format_duplicate_report(duplicates: Dict[str, List[Tuple[str, int]]]) -> str:
    """
    格式化重复类名报告
    """
    if not duplicates:
        return "✅ 未发现重复类名！所有配置类名唯一。"
    
    lines = []
    lines.append("=" * 80)
    lines.append(f"发现 {len(duplicates)} 个重复的类名")
    lines.append("=" * 80)
    lines.append("")
    
    # 按重复次数排序
    sorted_duplicates = sorted(
        duplicates.items(),
        key=lambda item: len(item[1]),
        reverse=True
    )
    
    for class_name, locations in sorted_duplicates:
        lines.append(f"类名: {class_name} （出现 {len(locations)} 次）")
        lines.append("-" * 80)
        
        for file_path, line_number in sorted(locations):
            lines.append(f"  - {file_path}:{line_number}")
        
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("建议：")
    lines.append("1. 为同名类添加领域后缀（如 BackpackComponentConfig vs BackpackTemplateConfig）")
    lines.append("2. 在各子包的 __init__.py 中使用别名导出以区分来源")
    lines.append("3. 在类的文档字符串中明确说明其用途和与其他同名类的区别")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """主函数"""
    parser = argparse.ArgumentParser(description="检测 engine/configs 下的重复类名")
    parser.add_argument("--root", type=str, default="", help="仓库根目录（默认自动推导）")
    parser.add_argument(
        "--config-dir",
        type=str,
        default="engine/configs",
        help="相对仓库根目录的配置目录（默认 engine/configs）",
    )
    parser.add_argument(
        "--fail-on-duplicates",
        action="store_true",
        help="发现重复类名时返回非零退出码（用于 CI/强约束场景；默认仅输出报告不失败）",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    project_root = Path(args.root).resolve() if args.root else get_workspace_root()
    config_dir = (project_root / str(args.config_dir)).resolve()

    print(f"正在扫描 {config_dir} ...")
    file_classes = scan_config_directory(project_root, config_dir)
    
    total_files = len(file_classes)
    total_classes = sum(len(classes) for classes in file_classes.values())
    print(f"扫描完成：{total_files} 个文件，{total_classes} 个类定义")

    if total_files == 0:
        raise SystemExit(f"[ERROR] 扫描到 0 个 Python 文件：{config_dir}（脚本可能仍指向旧目录）")
    print()
    
    duplicates = find_duplicate_classes(file_classes)
    report = format_duplicate_report(duplicates)
    print(report)
    
    # 返回状态码：默认仅输出报告不失败（便于在团队尚未收敛命名时也能接入 CI 做“不会崩”的守护）
    if bool(args.fail_on_duplicates) and len(duplicates) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

