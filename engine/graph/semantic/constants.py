from __future__ import annotations

# ===== GraphModel.metadata 语义元数据 keys（由 GraphSemanticPass 单点写入）=====

SIGNAL_BINDINGS_METADATA_KEY: str = "signal_bindings"
STRUCT_BINDINGS_METADATA_KEY: str = "struct_bindings"

# ===== NodeModel.input_constants 的“隐藏稳定 ID”键（供 Pass 推导/回填）=====
#
# 设计动机：
# - UI/代码更偏向在“选择端口”里展示显示名（例如“信号名”“结构体名”）；
# - 但仅凭显示名可能在“重名/改名/跨包聚合”场景出现歧义；
# - 因此 Pass 会把已解析出的稳定 ID 写入隐藏键，作为下一次推导的首选来源。

#
# 注意：键名与 `engine.graph.common.SIGNAL_ID_HINT_CONSTANT_KEY/STRUCT_ID_HINT_CONSTANT_KEY` 保持一致，
# 以避免出现多套隐藏键导致的迁移与推导分叉。

from engine.graph.common import (  # noqa: E402
    SIGNAL_ID_HINT_CONSTANT_KEY,
    STRUCT_ID_HINT_CONSTANT_KEY,
)

SEMANTIC_SIGNAL_ID_CONSTANT_KEY: str = SIGNAL_ID_HINT_CONSTANT_KEY
SEMANTIC_STRUCT_ID_CONSTANT_KEY: str = STRUCT_ID_HINT_CONSTANT_KEY


