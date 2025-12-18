"""复合节点代码生成器（应用层）。

目标：
- 输入：`engine.nodes.advanced_node_features.CompositeNodeConfig`（中立产物）
- 输出：复合节点 Python 源码（**类格式**，带 `@composite_class` 标记）

为什么不再生成“函数格式”：
- 资源库复合节点与引擎解析器以类格式为唯一可闭环的落盘格式；
- 复合节点校验规则（例如禁止列表/字典字面量）也与“函数格式可执行代码”不一致；
- UI 需要“可视化编辑→落盘→再次加载/校验”闭环，必须保证生成产物能被解析器读取。

实现策略（兼顾校验规则）：
- 文件内写入 `COMPOSITE_PAYLOAD_JSON`（多行字符串）承载 `CompositeNodeConfig.serialize()` 的 JSON；
- 引擎侧解析器优先读取该 JSON 直接还原 `CompositeNodeConfig`，避免把子图再编码成 Python 控制流/调用表达式；
- 为避免触发 `NoListDictLiteralRule`，生成文件中 **不出现** 顶层 list/dict 字面量。
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from engine.graph.common import (
    VarNameCounter,
)
from engine.nodes.advanced_node_features import CompositeNodeConfig, VirtualPinConfig
from engine.nodes.node_definition_loader import NodeDef


class CompositeCodeGenerator:
    """复合节点代码生成器 - 生成类格式（@composite_class）的复合节点代码（应用层）。"""

    def __init__(self, node_library: Optional[Dict[str, NodeDef]] = None):
        self.node_library = node_library or {}
        self._var_name_counter: VarNameCounter = VarNameCounter()

    def generate_code(self, composite: CompositeNodeConfig) -> str:
        self._var_name_counter = VarNameCounter()
        lines: List[str] = []

        lines.extend(self._generate_header(composite))
        lines.append("")
        lines.extend(self._generate_imports(composite))
        lines.append("")
        lines.extend(self._generate_payload(composite))
        lines.append("")
        lines.extend(self._generate_class_stub(composite))
        return "\n".join(lines)

    def _generate_header(self, composite: CompositeNodeConfig) -> List[str]:
        lines = ['"""']
        lines.append(f"composite_id: {composite.composite_id}")
        lines.append(f"node_name: {composite.node_name}")
        lines.append(f"node_description: {composite.node_description}")
        lines.append(f"scope: {composite.scope}")
        lines.append(f"folder_path: {composite.folder_path}")
        lines.append('"""')
        return lines

    def _generate_imports(self, composite: CompositeNodeConfig) -> List[str]:
        _ = composite
        lines: List[str] = []
        lines.append("from __future__ import annotations")
        lines.append("")
        lines.append("# 让该文件可在任意工作目录下被直接 import：注入 project_root/assets 到 sys.path（不要注入 app 目录）")
        lines.append("import sys")
        lines.append("from pathlib import Path")
        lines.append("")
        lines.append("PROJECT_ROOT = Path(__file__).resolve()")
        lines.append("for _ in range(12):")
        lines.append("    if (PROJECT_ROOT / 'pyrightconfig.json').exists():")
        lines.append("        break")
        lines.append("    if (PROJECT_ROOT / 'engine').exists() and (PROJECT_ROOT / 'app').exists():")
        lines.append("        break")
        lines.append("    PROJECT_ROOT = PROJECT_ROOT.parent")
        lines.append("ASSETS_ROOT = PROJECT_ROOT / 'assets'")
        lines.append("if str(PROJECT_ROOT) not in sys.path:")
        lines.append("    sys.path.insert(0, str(PROJECT_ROOT))")
        lines.append("if str(ASSETS_ROOT) not in sys.path:")
        lines.append("    sys.path.insert(1, str(ASSETS_ROOT))")
        lines.append("")
        lines.append("from engine.nodes.composite_spec import composite_class")
        return lines
    def _generate_payload(self, composite: CompositeNodeConfig) -> List[str]:
        payload = composite.serialize()
        payload_json = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        lines: List[str] = []
        lines.append("COMPOSITE_PAYLOAD_FORMAT_VERSION = 1")
        lines.append('COMPOSITE_PAYLOAD_JSON = r"""')
        lines.extend(payload_json.splitlines())
        lines.append('"""')
        return lines

    def _generate_class_stub(self, composite: CompositeNodeConfig) -> List[str]:
        """生成最小类壳，保证文件能被“类格式复合节点”扫描器识别。"""
        class_name = composite.node_name
        lines: List[str] = []
        lines.append("@composite_class")
        lines.append(f"class {class_name}:")
        lines.append('    """由可视化编辑器落盘的复合节点。逻辑子图保存在 COMPOSITE_PAYLOAD_JSON 中。"""')
        lines.append("    pass")
        return lines
