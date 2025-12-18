from __future__ import annotations

"""结构体系统领域服务入口。

本子包集中承载与“结构体定义 / 结构体绑定 / 校验协作”相关的纯引擎层逻辑，
为其他引擎子模块提供统一的领域 API，避免在各处零散地硬编码结构体特例。

暴露的核心组件：
- StructDefinitionRepository / get_default_struct_repository
"""

from .definition_repository import (  # noqa: F401
    StructDefinitionRepository,
    get_default_struct_repository,
    invalidate_default_struct_repository_cache,
)


