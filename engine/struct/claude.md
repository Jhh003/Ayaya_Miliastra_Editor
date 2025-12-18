## 目录用途
结构体系统领域层：集中提供“结构体定义”的只读仓库与与校验协作的公共接口，供解析器、校验器与 UI 统一复用。

## 当前状态
- 对外入口：`engine.struct.get_default_struct_repository()`。
- 结构体定义由 `engine.resources.definition_schema_view` 从 `assets/资源库/管理配置/结构体定义/**.py` 聚合加载，仓库在边界处执行严格 schema 校验。

## 注意事项
- 严禁在调用方自行解析结构体 payload（例如到处 `payload.get("value")` / `payload.get("struct_ype")`）；必须通过仓库 API 获取字段、类型与 ID 解析结果。
- 不提供历史字段兼容：旧字段（如 `struct_ype` / `value` / `lenth` / `key` 等）应在资源层清理，不允许继续出现。


