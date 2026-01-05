"""
graph_id: server_jiuquan_tiangongbu_wuzhijiangshi_01
graph_name: 天工部_物质匠师_物质属性编程
graph_type: server
folder_path: 九权
description: 九权天部 Roguelike 核心机制 - 天工部物质匠师的物质属性编程系统。
    核心资源：物质核心(MC)，攻击敌人或破坏环境获得1点MC，上限8点。
    消耗机制：消耗4点MC修改自身武器属性，持续5秒。
    效果框架：攻击力+50%、攻击范围+100%、攻击速度+50%。
    扩展设计支持：属性类型扩展、多属性叠加、环境属性修改、物质稳态。

节点图变量：
- 物质核心上限: 整数 = 8 [对外暴露]
- 属性修改消耗: 整数 = 4 [对外暴露]
- 属性修改持续时间: 浮点数 = 5.0 [对外暴露]
- 攻击力增益倍率: 浮点数 = 0.5 [对外暴露]
- 攻击范围增益倍率: 浮点数 = 1.0 [对外暴露]
- 攻击速度增益倍率: 浮点数 = 0.5 [对外暴露]
- 物质核心变量名: 字符串 = "物质核心" [对外暴露]
- 调试_当前物质核心: 整数 = 0
- 调试_当前激活属性: 字符串 = "无"
- 调试_属性剩余时间: 浮点数 = 0.0
"""

from __future__ import annotations

import pathlib
import sys

脚本文件路径 = pathlib.Path(__file__).resolve()
节点图根目录 = 脚本文件路径.parents[2]  # 节点图根目录（.../节点图）
服务器节点图目录 = 节点图根目录 / "server"  # 包含 server 侧 `_prelude.py` 的目录
if str(服务器节点图目录) not in sys.path:
    sys.path.insert(0, str(服务器节点图目录))

from _prelude import *  # noqa: F401,F403
from engine.graph.models.package_model import GraphVariableConfig


GRAPH_VARIABLES: list[GraphVariableConfig] = [
    GraphVariableConfig(
        name="物质核心上限",
        variable_type="整数",
        default_value=8,
        description="对外暴露：物质核心(MC)的最大上限值。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="属性修改消耗",
        variable_type="整数",
        default_value=4,
        description="对外暴露：触发属性修改效果所需消耗的物质核心数量。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="属性修改持续时间",
        variable_type="浮点数",
        default_value=5.0,
        description="对外暴露：属性修改效果的持续时间（秒）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="攻击力增益倍率",
        variable_type="浮点数",
        default_value=0.5,
        description="对外暴露：攻击力属性修改的增益倍率（0.5 = 增加50%）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="攻击范围增益倍率",
        variable_type="浮点数",
        default_value=1.0,
        description="对外暴露：攻击范围属性修改的增益倍率（1.0 = 增加100%）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="攻击速度增益倍率",
        variable_type="浮点数",
        default_value=0.5,
        description="对外暴露：攻击速度属性修改的增益倍率（0.5 = 增加50%）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="物质核心变量名",
        variable_type="字符串",
        default_value="物质核心",
        description="对外暴露：存储在实体自定义变量中的物质核心变量名。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="调试_当前物质核心",
        variable_type="整数",
        default_value=0,
        description="调试用：当前物质核心数量，便于在编辑器中观察。",
        is_exposed=False,
    ),
    GraphVariableConfig(
        name="调试_当前激活属性",
        variable_type="字符串",
        default_value="无",
        description="调试用：当前激活的属性修改类型。",
        is_exposed=False,
    ),
    GraphVariableConfig(
        name="调试_属性剩余时间",
        variable_type="浮点数",
        default_value=0.0,
        description="调试用：当前属性修改效果的剩余持续时间。",
        is_exposed=False,
    ),
]


class 天工部_物质匠师_物质属性编程:
    """天工部物质匠师的核心机制：物质属性编程系统。

    核心设计：
    1. 物质核心(MC)是核心资源，通过攻击敌人或破坏环境获取
    2. 消耗物质核心可临时修改自身武器属性
    3. 属性修改有持续时间限制，高消耗对应高强度效果

    平衡机制：
    - 属性修改有持续时间限制
    - 高消耗对应高强度效果
    - 环境修改有范围限制，避免全局影响

    扩展设计方向：
    - 属性类型扩展：武器附带元素伤害、攻击穿透率、攻击吸血
    - 多属性叠加：消耗更多MC同时获得攻击力和攻击速度提升
    - 环境属性修改：将地面变为沼泽（减速）、将敌人武器变为玻璃（降低攻击力）
    - 物质稳态：永久修改武器属性，消耗更多MC
    """

    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

        from app.runtime.engine.node_graph_validator import validate_node_graph

        validate_node_graph(self.__class__)

    # ---------------------------- 事件：实体创建时 ----------------------------
    def on_实体创建时(self, 事件源实体, 事件源GUID):
        """实体创建时：初始化物质核心为0。"""
        自身实体: "实体" = 获取自身实体(self.game)
        物质核心变量名: "字符串" = 获取节点图变量(self.game, 变量名="物质核心变量名")

        # 初始化物质核心
        设置自定义变量(
            self.game,
            目标实体=自身实体,
            变量名=物质核心变量名,
            变量值=0,
            是否触发事件=False,
        )
        设置自定义变量(
            self.game,
            目标实体=自身实体,
            变量名="当前激活属性",
            变量值="无",
            是否触发事件=False,
        )

        # 更新调试变量
        设置节点图变量(self.game, 变量名="调试_当前物质核心", 变量值=0, 是否触发事件=False)
        设置节点图变量(self.game, 变量名="调试_当前激活属性", 变量值="无", 是否触发事件=False)
        设置节点图变量(self.game, 变量名="调试_属性剩余时间", 变量值=0.0, 是否触发事件=False)

    # ---------------------------- 事件：造成伤害时 ----------------------------
    def on_造成伤害时(self, 事件源实体, 事件源GUID, 受击实体, 受击实体GUID, 伤害值):
        """攻击敌人时：获得1点物质核心。"""
        自身实体: "实体" = 获取自身实体(self.game)
        物质核心变量名: "字符串" = 获取节点图变量(self.game, 变量名="物质核心变量名")
        物质核心上限: "整数" = 获取节点图变量(self.game, 变量名="物质核心上限")

        # 获取当前物质核心
        当前物质核心: "整数" = 获取自定义变量(
            self.game,
            目标实体=自身实体,
            变量名=物质核心变量名,
        )

        # 检查是否已达上限
        未满: "布尔值" = 数值小于(self.game, 左值=当前物质核心, 右值=物质核心上限)

        if 未满:
            # 增加1点物质核心
            新物质核心: "整数" = 加法运算(self.game, 左值=当前物质核心, 右值=1)
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名=物质核心变量名,
                变量值=新物质核心,
                是否触发事件=False,
            )
            设置节点图变量(self.game, 变量名="调试_当前物质核心", 变量值=新物质核心, 是否触发事件=False)

    # ---------------------------- 信号：触发攻击力属性修改 ----------------------------
    def on_物质匠师_激活攻击力增强(self, 事件源实体, 事件源GUID, 信号来源实体):
        """触发攻击力属性修改：消耗物质核心，临时增加攻击力。"""
        自身实体: "实体" = 获取自身实体(self.game)
        物质核心变量名: "字符串" = 获取节点图变量(self.game, 变量名="物质核心变量名")
        属性修改消耗: "整数" = 获取节点图变量(self.game, 变量名="属性修改消耗")
        属性修改持续时间: "浮点数" = 获取节点图变量(self.game, 变量名="属性修改持续时间")

        当前物质核心: "整数" = 获取自定义变量(
            self.game,
            目标实体=自身实体,
            变量名=物质核心变量名,
        )
        可以触发: "布尔值" = 数值大于等于(self.game, 左值=当前物质核心, 右值=属性修改消耗)

        if 可以触发:
            # 消耗物质核心
            剩余物质核心: "整数" = 减法运算(self.game, 左值=当前物质核心, 右值=属性修改消耗)
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名=物质核心变量名,
                变量值=剩余物质核心,
                是否触发事件=False,
            )
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名="当前激活属性",
                变量值="攻击力增强",
                是否触发事件=False,
            )

            # 更新调试变量
            设置节点图变量(self.game, 变量名="调试_当前物质核心", 变量值=剩余物质核心, 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_当前激活属性", 变量值="攻击力增强", 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_属性剩余时间", 变量值=属性修改持续时间, 是否触发事件=False)

            # 开启属性效果结束定时器
            开启定时器(
                self.game,
                定时器名称="攻击力增强定时器",
                触发间隔=属性修改持续时间,
                是否循环=False,
            )

            # 发送信号通知属性修改激活
            发送信号(
                self.game,
                信号名="物质匠师_属性修改激活",
                属性类型="攻击力增强",
            )

    # ---------------------------- 信号：触发攻击范围属性修改 ----------------------------
    def on_物质匠师_激活攻击范围增强(self, 事件源实体, 事件源GUID, 信号来源实体):
        """触发攻击范围属性修改：消耗物质核心，临时增加攻击范围。"""
        自身实体: "实体" = 获取自身实体(self.game)
        物质核心变量名: "字符串" = 获取节点图变量(self.game, 变量名="物质核心变量名")
        属性修改消耗: "整数" = 获取节点图变量(self.game, 变量名="属性修改消耗")
        属性修改持续时间: "浮点数" = 获取节点图变量(self.game, 变量名="属性修改持续时间")

        当前物质核心: "整数" = 获取自定义变量(
            self.game,
            目标实体=自身实体,
            变量名=物质核心变量名,
        )
        可以触发: "布尔值" = 数值大于等于(self.game, 左值=当前物质核心, 右值=属性修改消耗)

        if 可以触发:
            # 消耗物质核心
            剩余物质核心: "整数" = 减法运算(self.game, 左值=当前物质核心, 右值=属性修改消耗)
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名=物质核心变量名,
                变量值=剩余物质核心,
                是否触发事件=False,
            )
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名="当前激活属性",
                变量值="攻击范围增强",
                是否触发事件=False,
            )

            # 更新调试变量
            设置节点图变量(self.game, 变量名="调试_当前物质核心", 变量值=剩余物质核心, 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_当前激活属性", 变量值="攻击范围增强", 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_属性剩余时间", 变量值=属性修改持续时间, 是否触发事件=False)

            # 开启属性效果结束定时器
            开启定时器(
                self.game,
                定时器名称="攻击范围增强定时器",
                触发间隔=属性修改持续时间,
                是否循环=False,
            )

            # 发送信号通知属性修改激活
            发送信号(
                self.game,
                信号名="物质匠师_属性修改激活",
                属性类型="攻击范围增强",
            )

    # ---------------------------- 信号：触发攻击速度属性修改 ----------------------------
    def on_物质匠师_激活攻击速度增强(self, 事件源实体, 事件源GUID, 信号来源实体):
        """触发攻击速度属性修改：消耗物质核心，临时增加攻击速度。"""
        自身实体: "实体" = 获取自身实体(self.game)
        物质核心变量名: "字符串" = 获取节点图变量(self.game, 变量名="物质核心变量名")
        属性修改消耗: "整数" = 获取节点图变量(self.game, 变量名="属性修改消耗")
        属性修改持续时间: "浮点数" = 获取节点图变量(self.game, 变量名="属性修改持续时间")

        当前物质核心: "整数" = 获取自定义变量(
            self.game,
            目标实体=自身实体,
            变量名=物质核心变量名,
        )
        可以触发: "布尔值" = 数值大于等于(self.game, 左值=当前物质核心, 右值=属性修改消耗)

        if 可以触发:
            # 消耗物质核心
            剩余物质核心: "整数" = 减法运算(self.game, 左值=当前物质核心, 右值=属性修改消耗)
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名=物质核心变量名,
                变量值=剩余物质核心,
                是否触发事件=False,
            )
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名="当前激活属性",
                变量值="攻击速度增强",
                是否触发事件=False,
            )

            # 更新调试变量
            设置节点图变量(self.game, 变量名="调试_当前物质核心", 变量值=剩余物质核心, 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_当前激活属性", 变量值="攻击速度增强", 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_属性剩余时间", 变量值=属性修改持续时间, 是否触发事件=False)

            # 开启属性效果结束定时器
            开启定时器(
                self.game,
                定时器名称="攻击速度增强定时器",
                触发间隔=属性修改持续时间,
                是否循环=False,
            )

            # 发送信号通知属性修改激活
            发送信号(
                self.game,
                信号名="物质匠师_属性修改激活",
                属性类型="攻击速度增强",
            )

    # ---------------------------- 事件：定时器触发时 ----------------------------
    def on_定时器触发时(self, 事件源实体, 事件源GUID, 定时器名称):
        """定时器触发时：处理属性修改效果的结束。"""
        自身实体: "实体" = 获取自身实体(self.game)

        match 定时器名称:
            case "攻击力增强定时器":
                设置自定义变量(
                    self.game,
                    目标实体=自身实体,
                    变量名="当前激活属性",
                    变量值="无",
                    是否触发事件=False,
                )
                设置节点图变量(self.game, 变量名="调试_当前激活属性", 变量值="无", 是否触发事件=False)
                设置节点图变量(self.game, 变量名="调试_属性剩余时间", 变量值=0.0, 是否触发事件=False)
                发送信号(
                    self.game,
                    信号名="物质匠师_属性修改结束",
                    属性类型="攻击力增强",
                )
            case "攻击范围增强定时器":
                设置自定义变量(
                    self.game,
                    目标实体=自身实体,
                    变量名="当前激活属性",
                    变量值="无",
                    是否触发事件=False,
                )
                设置节点图变量(self.game, 变量名="调试_当前激活属性", 变量值="无", 是否触发事件=False)
                设置节点图变量(self.game, 变量名="调试_属性剩余时间", 变量值=0.0, 是否触发事件=False)
                发送信号(
                    self.game,
                    信号名="物质匠师_属性修改结束",
                    属性类型="攻击范围增强",
                )
            case "攻击速度增强定时器":
                设置自定义变量(
                    self.game,
                    目标实体=自身实体,
                    变量名="当前激活属性",
                    变量值="无",
                    是否触发事件=False,
                )
                设置节点图变量(self.game, 变量名="调试_当前激活属性", 变量值="无", 是否触发事件=False)
                设置节点图变量(self.game, 变量名="调试_属性剩余时间", 变量值=0.0, 是否触发事件=False)
                发送信号(
                    self.game,
                    信号名="物质匠师_属性修改结束",
                    属性类型="攻击速度增强",
                )
            case _:
                return

    # ---------------------------- 注册事件处理器 ----------------------------
    def register_handlers(self):
        self.game.register_event_handler(
            "实体创建时",
            self.on_实体创建时,
            owner=self.owner_entity,
        )
        self.game.register_event_handler(
            "造成伤害时",
            self.on_造成伤害时,
            owner=self.owner_entity,
        )
        self.game.register_event_handler(
            "物质匠师_激活攻击力增强",
            self.on_物质匠师_激活攻击力增强,
            owner=self.owner_entity,
        )
        self.game.register_event_handler(
            "物质匠师_激活攻击范围增强",
            self.on_物质匠师_激活攻击范围增强,
            owner=self.owner_entity,
        )
        self.game.register_event_handler(
            "物质匠师_激活攻击速度增强",
            self.on_物质匠师_激活攻击速度增强,
            owner=self.owner_entity,
        )
        self.game.register_event_handler(
            "定时器触发时",
            self.on_定时器触发时,
            owner=self.owner_entity,
        )


if __name__ == "__main__":
    from app.runtime.engine.node_graph_validator import validate_file

    自身文件路径 = pathlib.Path(__file__).resolve()
    是否通过, 错误列表, 警告列表 = validate_file(自身文件路径)
    print("=" * 80)
    print(f"节点图自检: {自身文件路径.name}")
    print(f"文件: {自身文件路径}")
    if 是否通过:
        print("结果: 通过")
    else:
        print(f"结果: 未通过（错误: {len(错误列表)}，警告: {len(警告列表)}）")
        if 错误列表:
            print("\n错误明细:")
            for 序号, 错误文本 in enumerate(错误列表, start=1):
                print(f"  [{序号}] {错误文本}")
        if 警告列表:
            print("\n警告明细:")
            for 序号, 警告文本 in enumerate(警告列表, start=1):
                print(f"  [{序号}] {警告文本}")
    print("=" * 80)
    if not 是否通过:
        sys.exit(1)
