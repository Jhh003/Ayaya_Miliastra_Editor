# 校验工具目录（tools/validate）

## 目录用途
集中存放“校验入口类脚本”（validate/benchmark/check 入口），统一从项目根目录执行。

## 入口脚本
- `validate_graphs.py`：节点图 + 复合节点校验（调用 `engine.validate.validate_files`；复合节点的 UI 同款结构校验统一复用 `engine.validate.collect_composite_structural_issues(...)`，可用 `--no-composite-struct-check` 关闭）
- `validate_package.py`：存档包索引/挂载关系综合校验（调用 `engine.validate.ComprehensiveValidator`）
- `validate_graph_cache_integrity.py`：graph_cache JSON 结构一致性检查
- `validate_ui_automation_contracts.py`：UI/automation 冒烟级回归自检入口（UI 资源库关键页面构造+刷新、自动化执行器协议关键方法签名一致性、graph_data 进程内缓存契约）
- `benchmark_validate.py`：全量校验性能基准
- `validate_resource_library_overview.py`：资源库与功能包索引构建/总览校验（数量概览）
- `check_validate_graph_line_numbers.py`：校验报错行号输出的辅助脚本

## 注意事项
- 仅作为 CLI 编排与输出层，不承载引擎规则实现；核心校验逻辑应留在 `engine/*`。
- 执行路径默认假定为项目根目录；统一使用 `python -X utf8 -m tools.validate.<module>` 运行以避免导入根不一致与编码问题。
- 校验入口的资源上下文构建应统一走 `engine.resources.resource_context`（如 `build_resource_context/build_resource_index_context/build_resource_manager`），由其负责初始化 `settings.set_config_path(workspace_root)`，避免 settings 未初始化导致缓存路径漂移/解析阶段抛错。
- 本目录下脚本为校验的**唯一标准入口**；`tools/` 根目录不再保留同名兼容入口。
- 存档包索引（功能包索引）目录为 `assets/资源库/功能包索引/`；若校验提示“未找到任何存档包索引”，通常意味着该目录为空或被移动/误删。
- 节点图目录 `assets/资源库/节点图/` 允许存在以下划线开头的内部脚本（如 `_prelude.py`）；全量校验默认会跳过这些文件，只校验可作为节点图入口的 Graph Code 文件。
- 节点图目录中允许存在带“校验”字样的辅助脚本（如 `校验节点图.py`）；全量校验默认会跳过这类文件，只校验可作为节点图入口的 Graph Code 文件。
- 复合节点库目录 `assets/资源库/复合节点库/` 允许包含校验脚本与辅助模块；全量校验默认仅纳入 `composite_*.py` 作为复合节点定义文件（筛选规则统一复用 `engine.nodes.composite_file_policy`）。


