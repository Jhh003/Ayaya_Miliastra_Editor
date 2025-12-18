from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，便于在 pytest 下稳定导入 `app`、`engine` 等包。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT_STR = str(PROJECT_ROOT)
if PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_STR)

# 注意：不要将 `<repo>/app` 加入 sys.path。
# 否则 `app/ui` 会变成顶层包 `ui`，从而导致 `ui.*` 与 `app.ui.*` 并存并触发“同名类不是同一个类”。

# 初始化 settings 的 workspace_path 单一真源，供布局/节点库等模块稳定推导工作区。
from engine.configs.settings import settings  # noqa: E402

settings.set_config_path(PROJECT_ROOT)
settings.load()

