"""
graph_id: server_jiuquan_qintianji_yinguolian_01
graph_name: 钦天监_因果命师_因果链追踪
graph_type: server
folder_path: 九权
description: 九权天部 Roguelike 核心机制 - 钦天监因果命师的因果链追踪系统。
    核心资源：因果点(CP)，攻击命中时有10%概率获得1点CP，上限10点。
    消耗机制：消耗固定CP值触发"必然效果"（必然暴击）。
    扩展设计支持：资源生成扩展、效果多样性、因果连锁、因果债务。

节点图变量：
- 因果点上限: 整数 = 10 [对外暴露]
- 因果点获取概率: 浮点数 = 0.1 [对外暴露]
- 必然暴击消耗: 整数 = 5 [对外暴露]
- 暴击伤害倍率: 浮点数 = 2.0 [对外暴露]
- 因果点变量名: 字符串 = "因果点" [对外暴露]
- 调试_当前因果点: 整数 = 0
- 调试_最近触发效果: 字符串 = "无"
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
        name="因果点上限",
        variable_type="整数",
        default_value=10,
        description="对外暴露：因果点(CP)的最大上限值，限制爆发强度。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="因果点获取概率",
        variable_type="浮点数",
        default_value=0.1,
        description="对外暴露：攻击命中时获得1点因果点的概率（0.1 = 10%）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="必然暴击消耗",
        variable_type="整数",
        default_value=5,
        description="对外暴露：触发必然暴击效果所需消耗的因果点数量。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="暴击伤害倍率",
        variable_type="浮点数",
        default_value=2.0,
        description="对外暴露：必然暴击时的伤害倍率（基础暴击倍数上限）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="因果点变量名",
        variable_type="字符串",
        default_value="因果点",
        description="对外暴露：存储在实体自定义变量中的因果点变量名。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="调试_当前因果点",
        variable_type="整数",
        default_value=0,
        description="调试用：当前因果点数量，便于在编辑器中观察。",
        is_exposed=False,
    ),
    GraphVariableConfig(
        name="调试_最近触发效果",
        variable_type="字符串",
        default_value="无",
        description="调试用：最近一次触发的必然效果名称。",
        is_exposed=False,
    ),
]


class 钦天监_因果命师_因果链追踪:
    """钦天监因果命师的核心机制：因果链追踪系统。

    核心设计：
    1. 因果点(CP)是核心资源，通过攻击命中概率获取
    2. 消耗因果点可触发"必然效果"（初始为必然暴击）
    3. 因果点上限限制爆发强度，概率获取避免资源积累过快

    扩展设计方向：
    - 资源生成扩展：击杀敌人额外获得CP；连续攻击同一目标，CP获取概率递增
    - 效果多样性：必然闪避、必然命中、必然触发特效
    - 因果连锁：必然暴击后，有概率额外获得CP或触发另一个必然效果
    - 因果债务：允许预支CP，后续需要偿还
    """

    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

        from app.runtime.engine.node_graph_validator import validate_node_graph

        validate_node_graph(self.__class__)

    # ---------------------------- 事件：实体创建时 ----------------------------
    def on_实体创建时(self, 事件源实体, 事件源GUID):
        """实体创建时：初始化因果点为0。"""
        自身实体: "实体" = 获取自身实体(self.game)
        因果点变量名: "字符串" = 获取节点图变量(self.game, 变量名="因果点变量名")

        # 初始化因果点为0
        设置自定义变量(
            self.game,
            目标实体=自身实体,
            变量名=因果点变量名,
            变量值=0,
            是否触发事件=False,
        )
        设置节点图变量(
            self.game,
            变量名="调试_当前因果点",
            变量值=0,
            是否触发事件=False,
        )
        设置节点图变量(
            self.game,
            变量名="调试_最近触发效果",
            变量值="无",
            是否触发事件=False,
        )

    # ---------------------------- 事件：造成伤害时 ----------------------------
    def on_造成伤害时(self, 事件源实体, 事件源GUID, 受击实体, 受击实体GUID, 伤害值):
        """攻击命中时：根据概率获取因果点。"""
        自身实体: "实体" = 获取自身实体(self.game)
        因果点变量名: "字符串" = 获取节点图变量(self.game, 变量名="因果点变量名")
        因果点获取概率: "浮点数" = 获取节点图变量(self.game, 变量名="因果点获取概率")
        因果点上限: "整数" = 获取节点图变量(self.game, 变量名="因果点上限")

        # 获取当前因果点
        当前因果点: "整数" = 获取自定义变量(
            self.game,
            目标实体=自身实体,
            变量名=因果点变量名,
        )

        # 检查是否已达上限
        是否已满: "布尔值" = 数值大于等于(
            self.game,
            左值=当前因果点,
            右值=因果点上限,
        )
        if 是否已满:
            return

        # 概率判定是否获取因果点
        随机值: "浮点数" = 获取随机浮点数(self.game, 下限=0.0, 上限=1.0)
        是否获取: "布尔值" = 数值小于(
            self.game,
            左值=随机值,
            右值=因果点获取概率,
        )

        if 是否获取:
            # 增加1点因果点
            新因果点: "整数" = 加法运算(
                self.game,
                左值=当前因果点,
                右值=1,
            )
            # 确保不超过上限
            最终因果点: "整数" = 取最小值(
                self.game,
                输入1=新因果点,
                输入2=因果点上限,
            )
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名=因果点变量名,
                变量值=最终因果点,
                是否触发事件=False,
            )
            设置节点图变量(
                self.game,
                变量名="调试_当前因果点",
                变量值=最终因果点,
                是否触发事件=False,
            )

    # ---------------------------- 事件：技能释放前 ----------------------------
    def on_技能释放前(self, 事件源实体, 事件源GUID, 技能ID):
        """技能释放前：检查是否满足触发必然暴击的条件，并消耗因果点。"""
        自身实体: "实体" = 获取自身实体(self.game)
        因果点变量名: "字符串" = 获取节点图变量(self.game, 变量名="因果点变量名")
        必然暴击消耗: "整数" = 获取节点图变量(self.game, 变量名="必然暴击消耗")

        # 获取当前因果点
        当前因果点: "整数" = 获取自定义变量(
            self.game,
            目标实体=自身实体,
            变量名=因果点变量名,
        )

        # 检查是否有足够的因果点触发必然暴击
        可以触发: "布尔值" = 数值大于等于(
            self.game,
            左值=当前因果点,
            右值=必然暴击消耗,
        )

        if 可以触发:
            # 消耗因果点
            剩余因果点: "整数" = 减法运算(
                self.game,
                左值=当前因果点,
                右值=必然暴击消耗,
            )
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名=因果点变量名,
                变量值=剩余因果点,
                是否触发事件=False,
            )
            设置节点图变量(
                self.game,
                变量名="调试_当前因果点",
                变量值=剩余因果点,
                是否触发事件=False,
            )

            # 标记下次攻击必然暴击
            设置自定义变量(
                self.game,
                目标实体=自身实体,
                变量名="必然暴击激活",
                变量值=True,
                是否触发事件=False,
            )
            设置节点图变量(
                self.game,
                变量名="调试_最近触发效果",
                变量值="必然暴击",
                是否触发事件=False,
            )

            # 发送信号通知必然效果触发
            发送信号(
                self.game,
                信号名="因果命师_必然效果触发",
                效果类型="必然暴击",
            )

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
            "技能释放前",
            self.on_技能释放前,
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
