## 目录用途
- 承载自动化执行器中所有“节点配置类”高层步骤实现，包括参数注入、Settings 行定位以及多分支分支输出等逻辑。
- 与 `app.automation.editor.editor_connect` 协作，通过纯函数入口提供 `execute_config_node_merged`、分支端口添加与分支输出配置等能力，不直接依赖 UI 组件。

## 当前状态
- `config_params.py` / `config_node_steps.py`：负责普通节点参数配置，将一次性的大步骤拆分为可测试的小步骤（端口定位、Warning 搜索区域计算、布尔/枚举/普通参数输入等），并复用端口识别与向量输入等通用工具。
- `branch_config.py`：聚焦多分支类节点的端口添加与分支输出配置逻辑，基于图模型的端口顺序与视觉识别结果，按“分支名 → 流程输出口”的映射为每个分支输入匹配值，同时复用 Warning 区域查找与参数输入流程。
- 其余模块提供 Settings 扫描、配置辅助与公共工具函数，统一依赖 `executor_utils` 与 `vision` 提供的截图/日志/端口识别能力。

## 注意事项
- 不在本目录中新增 `try/except` 吞掉异常；配置失败应通过返回值与日志显式暴露，由上层决定是否重试或中止执行。
- 仅通过 `EditorExecutorWithViewport` 等协议访问执行器能力，禁止直接调用私有方法或依赖具体 UI 实现细节。
- 新增配置步骤时应优先拆分为“小步骤 + 入口函数”的结构，方便在无真实编辑器环境下编写单元测试与模拟调用。

## 目录用途
- 负责基于自动化执行器的各类“配置步骤”：节点参数注入、分支输出配置、Settings 扫描与相关辅助工具。

## 模块说明
- `config_params.py`：节点输入参数批量配置入口，调度截图、端口定位与 Warning 区域查找等步骤。
- `config_node_steps.py`：参数配置与 Warning 搜索的可复用步骤实现，复用端口快照与视觉识别结果。
- `config_params_helpers.py`：端口序号映射、端口候选过滤与调试日志等纯逻辑辅助函数。
- `settings_scanner.py`：Settings 面板扫描、映射与结构化输出。
- `branch_config.py`：分支输出端口添加与匹配值配置，沿用参数配置步骤中的端口定位与 Warning 处理；
  其中 `click_add_icon_within_node()` 会在一次模板匹配未能在节点内找到 Add 按钮时，先基于节点中心在画布区域内寻找安全空白点，将鼠标移出节点到该空白位置后重新截图并重试模板匹配；若在画布区域内无法找到安全空白点，则通过明确日志提示前置条件失败并放弃本次 Add 重试，以降低因鼠标遮挡、局部 UI 状态或视口约束导致的误判。
- `signal_config.py`：信号绑定相关配置步骤，实现基于 `Signal.png` 模板与固定几何位移的“设置信号”执行逻辑（先点击 Signal，再点击其正下方一行输入区域并输入文本，最后在节点附近通过通用画布空白点击 helper 收尾），在节点图中为发送/监听信号节点注入信号标识；输入文本侧优先引导使用信号显示名称，在无法取得名称时才退回到使用绑定的信号 ID，以配合引擎层“信号名端口只接受显示名称”的约定。

## 注意事项
- 所有截图、模板匹配和端口识别必须经 `app.automation.capture` 与 `app.automation.vision`，不要在本目录直接访问底层实现。
- 不在这里引入新的 UI 依赖；所有交互通过执行器协议与可视化回调完成。
- 配置步骤应保持可重入与可缓存性，端口与 Warning 搜索结果优先复用快照和已有识别结果，避免重复全图识别。

## 当前状态速览
- 参数配置、分支配置与信号绑定均拆成可复用小步骤函数，便于单元测试与组合。
- 布尔/枚举参数在完成端口几何定位后，通过固定节奏点击完成状态切换或枚举选择，避免依赖具体控件实现差异。
- 三维向量等复合类型在 Warning 区域命中后，优先使用几何法一体化注入；若模板匹配失败，则回退到基于端口中心与 OCR 的通用 Fallback 路径；两条路径均复用 `ports.vector3_input_handler` 与 `vector3_ui_apply.apply_vector3_plan` 的统一轴级点击+文本注入流程，并通过 `AutomationStepContext` 打包日志/可视化/暂停钩子等运行时上下文，减少参数配置步骤中的样板代码。
- 参数与端口类型配置统一依赖 `core.node_snapshot.NodePortsSnapshotCache` 维护截图与端口缓存，在场景缓存开启时尽量复用同帧识别结果。
- 本目录仅承载“配置流程”相关逻辑，其它自动化能力请放在 `capture/`、`vision/`、`ports/` 或 `core/` 等子包中。

## 目录用途
- 封装“节点参数配置与分支配置”相关逻辑：参数值注入、配置步骤拆分、配置辅助工具等。
- 将端口级别的操作与高层“图步骤”区分开来，便于理解与测试。

## 当前状态
- 主要模块：
- `config_params.py`：节点参数配置主流程，以“每个参数一次截图”策略驱动 `NodePortsSnapshotCache`，同一参数内部共享同帧图像与端口列表，仅在完成输入后按需标记脏区，避免在 Warning 搜索阶段再次整帧截图；Warning 区域与模板匹配结果会按截图帧缓存，连续参数在同一帧上无需重复计算。
- `config_node_steps.py`：参数配置步骤拆分与编排，并提供 Warning / Fallback 公共辅助函数；输入端与分支输出端共用同一个 Warning 区域计算器，保持日志与阈值一致，端口中心复用判断统一调用 `config_params_helpers.check_center_used()`，端口候选列表统一通过 `app.automation.vision.list_ports` 提供以确保识别结果与后续几何搜索区域计算的一致性；在缺少端口识别函数时会记录日志并终止当前参数/Warning 区域计算，而不是抛出运行时异常。
- `config_params_helpers.py`：参数配置通用辅助函数，OCR 边界框归一化直接复用 `vision.ocr_utils.normalize_ocr_bbox`，并在计算输入端口序号时统一复用 `engine.graph.common.is_selection_input_port` 排除“选择端口”（如发送/监听信号的“信号名”、结构体相关节点的“结构体名”），保证模型端口序号与屏幕端口候选列表在存在选择控件时仍然对齐，避免将下方实际可编辑端口错认成上方选择端口。
- `settings_scanner.py`：Settings 按钮扫描与映射，复用 `app.automation.editor.node_snapshot.capture_node_ports_snapshot()` 以统一截图/端口识别路径，并依赖 `engine.nodes.port_index_mapper.map_port_index_to_name()` 完成端口名称映射；扫描结果以 `{node_id -> settings 列表}` 形式返回给调用者，并借助 `ports.settings_locator.collect_settings_rows()` 与端口筛选逻辑保持一致。
  - `branch_config.py`：分支端口新增与配置逻辑，并提供 `execute_add_with_icon_clicks()` 供变参/分支公用；`click_add_icon_within_node()` 支持复用外部截图，`execute_config_branch_outputs()` 维护节点截图与端口缓存，减少重复截图与 OCR。
- Warning 区域查找同时覆盖左右两侧：`config_node_steps.py` 内统一实现输入端与分支输出端的搜索区域计算，保证阈值与日志一致。
- 连续执行场景下，绝大多数“等待 X 秒”缓冲统一通过 `_exec_utils.log_wait_if_needed()` 控制；当 `executor.fast_chain_mode` 为 True 时自动跳过，避免连接/配置步骤之间停顿；少数局部流程在缺少该工具时会退化为固定时长的 `sleep_seconds()`，以保证在不同运行环境下也不会因为缺少工具函数而中断。

## 注意事项
- 具体的端口类型推断与类型设置逻辑由 `app.automation.ports` 提供，本目录调用其接口完成图级别配置。
- 新增配置流程时优先以“小步骤函数 + 编排函数”的形式组织，避免出现过长或难以测试的单体函数。
- 参数配置阶段复用 `app.automation.editor.node_snapshot.NodePortsSnapshotCache` 维护截图/节点 bbox/端口缓存，只有 UI 实际变化时才刷新，以避免高频截图和 OCR。
- 复用 `execute_add_with_icon_clicks()` 可统一控制单击 Add 的节奏与可视化输出，外层只需决定需要增加的数量及 `prefer_multi` 策略。
- `_NodeVisionContext` 的截图/端口缓存会直接传递给 Warning 区域计算，避免在同一帧上重复 `list_ports` 与 OCR。


