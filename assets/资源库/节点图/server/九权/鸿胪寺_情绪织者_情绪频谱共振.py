"""
graph_id: server_jiuquan_honglusi_qingxuzhizhe_01
graph_name: 鸿胪寺_情绪织者_情绪频谱共振
graph_type: server
folder_path: 九权
description: 九权天部 Roguelike 核心机制 - 鸿胪寺情绪织者的情绪频谱共振系统。
    核心资源：三种情绪值（愤怒、恐惧、绝望），每种上限8点。
    生成机制：攻击命中时根据敌人状态获得1点对应情绪值。
    消耗机制：消耗3点同类型情绪值触发"情绪共振"效果。
    效果框架：愤怒（范围伤害）、恐惧（群体减速）、绝望（降低攻击力）。
    扩展设计支持：情绪类型扩展、情绪融合、情绪过载、情绪共鸣。

节点图变量：
- 情绪值上限: 整数 = 8 [对外暴露]
- 情绪共振消耗: 整数 = 3 [对外暴露]
- 愤怒伤害值: 整数 = 50 [对外暴露]
- 愤怒伤害范围: 浮点数 = 5.0 [对外暴露]
- 恐惧减速比例: 浮点数 = 0.5 [对外暴露]
- 恐惧持续时间: 浮点数 = 3.0 [对外暴露]
- 绝望攻击降低比例: 浮点数 = 0.3 [对外暴露]
- 绝望持续时间: 浮点数 = 5.0 [对外暴露]
- 情绪衰减间隔: 浮点数 = 10.0 [对外暴露]
- 调试_当前愤怒值: 整数 = 0
- 调试_当前恐惧值: 整数 = 0
- 调试_当前绝望值: 整数 = 0
- 调试_最近触发共振: 字符串 = "无"
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
        name="情绪值上限",
        variable_type="整数",
        default_value=8,
        description="对外暴露：每种情绪值的最大上限。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="情绪共振消耗",
        variable_type="整数",
        default_value=3,
        description="对外暴露：触发情绪共振效果所需消耗的同类型情绪值数量。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="愤怒伤害值",
        variable_type="整数",
        default_value=50,
        description="对外暴露：愤怒共振造成的范围伤害基础值。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="愤怒伤害范围",
        variable_type="浮点数",
        default_value=5.0,
        description="对外暴露：愤怒共振的范围伤害半径。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="恐惧减速比例",
        variable_type="浮点数",
        default_value=0.5,
        description="对外暴露：恐惧共振造成的移动速度降低比例（0.5 = 降低50%）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="恐惧持续时间",
        variable_type="浮点数",
        default_value=3.0,
        description="对外暴露：恐惧共振减速效果的持续时间（秒）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="绝望攻击降低比例",
        variable_type="浮点数",
        default_value=0.3,
        description="对外暴露：绝望共振造成的敌人攻击力降低比例（0.3 = 降低30%）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="绝望持续时间",
        variable_type="浮点数",
        default_value=5.0,
        description="对外暴露：绝望共振攻击力降低效果的持续时间（秒）。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="情绪衰减间隔",
        variable_type="浮点数",
        default_value=10.0,
        description="对外暴露：情绪值自动衰减的时间间隔（秒），每次衰减1点。",
        is_exposed=True,
    ),
    GraphVariableConfig(
        name="调试_当前愤怒值",
        variable_type="整数",
        default_value=0,
        description="调试用：当前愤怒值，便于在编辑器中观察。",
        is_exposed=False,
    ),
    GraphVariableConfig(
        name="调试_当前恐惧值",
        variable_type="整数",
        default_value=0,
        description="调试用：当前恐惧值，便于在编辑器中观察。",
        is_exposed=False,
    ),
    GraphVariableConfig(
        name="调试_当前绝望值",
        variable_type="整数",
        default_value=0,
        description="调试用：当前绝望值，便于在编辑器中观察。",
        is_exposed=False,
    ),
    GraphVariableConfig(
        name="调试_最近触发共振",
        variable_type="字符串",
        default_value="无",
        description="调试用：最近一次触发的情绪共振类型。",
        is_exposed=False,
    ),
]


class 鸿胪寺_情绪织者_情绪频谱共振:
    """鸿胪寺情绪织者的核心机制：情绪频谱共振系统。

    核心设计：
    1. 三种独立的情绪值（愤怒、恐惧、绝望），分别对应不同效果
    2. 攻击命中时根据敌人状态获得对应情绪值
    3. 消耗3点同类型情绪值触发情绪共振效果
    4. 情绪值随时间缓慢衰减，鼓励主动消耗

    平衡机制：
    - 三种情绪值独立计算，避免单一情绪过度积累
    - 情绪共振效果有明确的范围和持续时间限制
    - 情绪值随时间缓慢衰减，鼓励主动消耗

    扩展设计方向：
    - 情绪类型扩展：喜悦（自身增益）、悲伤（敌人持续伤害）
    - 情绪融合：愤怒+恐惧=震慑；恐惧+绝望=崩溃
    - 情绪过载：单一情绪值满时触发额外效果
    - 情绪共鸣：与队友情绪产生共鸣
    """

    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

        from app.runtime.engine.node_graph_validator import validate_node_graph

        validate_node_graph(self.__class__)

    # ---------------------------- 事件：实体创建时 ----------------------------
    def on_实体创建时(self, 事件源实体, 事件源GUID):
        """实体创建时：初始化三种情绪值为0，并启动衰减定时器。"""
        自身实体: "实体" = 获取自身实体(self.game)

        # 初始化三种情绪值
        设置自定义变量(
            self.game,
            目标实体=自身实体,
            变量名="愤怒值",
            变量值=0,
            是否触发事件=False,
        )
        设置自定义变量(
            self.game,
            目标实体=自身实体,
            变量名="恐惧值",
            变量值=0,
            是否触发事件=False,
        )
        设置自定义变量(
            self.game,
            目标实体=自身实体,
            变量名="绝望值",
            变量值=0,
            是否触发事件=False,
        )

        # 更新调试变量
        设置节点图变量(self.game, 变量名="调试_当前愤怒值", 变量值=0, 是否触发事件=False)
        设置节点图变量(self.game, 变量名="调试_当前恐惧值", 变量值=0, 是否触发事件=False)
        设置节点图变量(self.game, 变量名="调试_当前绝望值", 变量值=0, 是否触发事件=False)
        设置节点图变量(self.game, 变量名="调试_最近触发共振", 变量值="无", 是否触发事件=False)

        # 启动情绪衰减定时器
        情绪衰减间隔: "浮点数" = 获取节点图变量(self.game, 变量名="情绪衰减间隔")
        开启定时器(
            self.game,
            定时器名称="情绪衰减定时器",
            触发间隔=情绪衰减间隔,
            是否循环=True,
        )

    # ---------------------------- 事件：造成伤害时 ----------------------------
    def on_造成伤害时(self, 事件源实体, 事件源GUID, 受击实体, 受击实体GUID, 伤害值):
        """攻击命中时：根据敌人状态获得对应情绪值。"""
        自身实体: "实体" = 获取自身实体(self.game)
        情绪值上限: "整数" = 获取节点图变量(self.game, 变量名="情绪值上限")

        # 根据敌人当前状态决定获取哪种情绪值
        # 简化逻辑：使用随机数决定获取哪种情绪（实际游戏中应根据敌人状态判断）
        随机情绪: "整数" = 获取随机整数(self.game, 下限=0, 上限=2)

        match 随机情绪:
            case 0:
                # 获取愤怒值
                当前愤怒: "整数" = 获取自定义变量(
                    self.game,
                    目标实体=自身实体,
                    变量名="愤怒值",
                )
                未满: "布尔值" = 数值小于(self.game, 左值=当前愤怒, 右值=情绪值上限)
                if 未满:
                    新愤怒: "整数" = 加法运算(self.game, 左值=当前愤怒, 右值=1)
                    设置自定义变量(
                        self.game,
                        目标实体=自身实体,
                        变量名="愤怒值",
                        变量值=新愤怒,
                        是否触发事件=False,
                    )
                    设置节点图变量(self.game, 变量名="调试_当前愤怒值", 变量值=新愤怒, 是否触发事件=False)
            case 1:
                # 获取恐惧值
                当前恐惧: "整数" = 获取自定义变量(
                    self.game,
                    目标实体=自身实体,
                    变量名="恐惧值",
                )
                未满: "布尔值" = 数值小于(self.game, 左值=当前恐惧, 右值=情绪值上限)
                if 未满:
                    新恐惧: "整数" = 加法运算(self.game, 左值=当前恐惧, 右值=1)
                    设置自定义变量(
                        self.game,
                        目标实体=自身实体,
                        变量名="恐惧值",
                        变量值=新恐惧,
                        是否触发事件=False,
                    )
                    设置节点图变量(self.game, 变量名="调试_当前恐惧值", 变量值=新恐惧, 是否触发事件=False)
            case 2:
                # 获取绝望值
                当前绝望: "整数" = 获取自定义变量(
                    self.game,
                    目标实体=自身实体,
                    变量名="绝望值",
                )
                未满: "布尔值" = 数值小于(self.game, 左值=当前绝望, 右值=情绪值上限)
                if 未满:
                    新绝望: "整数" = 加法运算(self.game, 左值=当前绝望, 右值=1)
                    设置自定义变量(
                        self.game,
                        目标实体=自身实体,
                        变量名="绝望值",
                        变量值=新绝望,
                        是否触发事件=False,
                    )
                    设置节点图变量(self.game, 变量名="调试_当前绝望值", 变量值=新绝望, 是否触发事件=False)

    # ---------------------------- 事件：定时器触发时 ----------------------------
    def on_定时器触发时(self, 事件源实体, 事件源GUID, 定时器名称):
        """定时器触发时：处理情绪值的自动衰减。"""
        是否情绪衰减: "布尔值" = 是否相等(self.game, 输入1=定时器名称, 输入2="情绪衰减定时器")
        if 是否情绪衰减:
            自身实体: "实体" = 获取自身实体(self.game)

            # 衰减愤怒值
            当前愤怒: "整数" = 获取自定义变量(self.game, 目标实体=自身实体, 变量名="愤怒值")
            愤怒大于零: "布尔值" = 数值大于(self.game, 左值=当前愤怒, 右值=0)
            if 愤怒大于零:
                新愤怒: "整数" = 减法运算(self.game, 左值=当前愤怒, 右值=1)
                设置自定义变量(self.game, 目标实体=自身实体, 变量名="愤怒值", 变量值=新愤怒, 是否触发事件=False)
                设置节点图变量(self.game, 变量名="调试_当前愤怒值", 变量值=新愤怒, 是否触发事件=False)

            # 衰减恐惧值
            当前恐惧: "整数" = 获取自定义变量(self.game, 目标实体=自身实体, 变量名="恐惧值")
            恐惧大于零: "布尔值" = 数值大于(self.game, 左值=当前恐惧, 右值=0)
            if 恐惧大于零:
                新恐惧: "整数" = 减法运算(self.game, 左值=当前恐惧, 右值=1)
                设置自定义变量(self.game, 目标实体=自身实体, 变量名="恐惧值", 变量值=新恐惧, 是否触发事件=False)
                设置节点图变量(self.game, 变量名="调试_当前恐惧值", 变量值=新恐惧, 是否触发事件=False)

            # 衰减绝望值
            当前绝望: "整数" = 获取自定义变量(self.game, 目标实体=自身实体, 变量名="绝望值")
            绝望大于零: "布尔值" = 数值大于(self.game, 左值=当前绝望, 右值=0)
            if 绝望大于零:
                新绝望: "整数" = 减法运算(self.game, 左值=当前绝望, 右值=1)
                设置自定义变量(self.game, 目标实体=自身实体, 变量名="绝望值", 变量值=新绝望, 是否触发事件=False)
                设置节点图变量(self.game, 变量名="调试_当前绝望值", 变量值=新绝望, 是否触发事件=False)

    # ---------------------------- 信号：触发愤怒共振 ----------------------------
    def on_情绪织者_触发愤怒共振(self, 事件源实体, 事件源GUID, 信号来源实体):
        """触发愤怒共振：消耗愤怒值，对范围内敌人造成伤害。"""
        自身实体: "实体" = 获取自身实体(self.game)
        情绪共振消耗: "整数" = 获取节点图变量(self.game, 变量名="情绪共振消耗")

        当前愤怒: "整数" = 获取自定义变量(self.game, 目标实体=自身实体, 变量名="愤怒值")
        可以触发: "布尔值" = 数值大于等于(self.game, 左值=当前愤怒, 右值=情绪共振消耗)

        if 可以触发:
            # 消耗愤怒值
            剩余愤怒: "整数" = 减法运算(self.game, 左值=当前愤怒, 右值=情绪共振消耗)
            设置自定义变量(self.game, 目标实体=自身实体, 变量名="愤怒值", 变量值=剩余愤怒, 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_当前愤怒值", 变量值=剩余愤怒, 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_最近触发共振", 变量值="愤怒共振", 是否触发事件=False)

            # 发送信号通知效果触发
            发送信号(
                self.game,
                信号名="情绪织者_共振效果触发",
                共振类型="愤怒",
            )

    # ---------------------------- 信号：触发恐惧共振 ----------------------------
    def on_情绪织者_触发恐惧共振(self, 事件源实体, 事件源GUID, 信号来源实体):
        """触发恐惧共振：消耗恐惧值，对范围内敌人施加减速效果。"""
        自身实体: "实体" = 获取自身实体(self.game)
        情绪共振消耗: "整数" = 获取节点图变量(self.game, 变量名="情绪共振消耗")

        当前恐惧: "整数" = 获取自定义变量(self.game, 目标实体=自身实体, 变量名="恐惧值")
        可以触发: "布尔值" = 数值大于等于(self.game, 左值=当前恐惧, 右值=情绪共振消耗)

        if 可以触发:
            # 消耗恐惧值
            剩余恐惧: "整数" = 减法运算(self.game, 左值=当前恐惧, 右值=情绪共振消耗)
            设置自定义变量(self.game, 目标实体=自身实体, 变量名="恐惧值", 变量值=剩余恐惧, 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_当前恐惧值", 变量值=剩余恐惧, 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_最近触发共振", 变量值="恐惧共振", 是否触发事件=False)

            # 发送信号通知效果触发
            发送信号(
                self.game,
                信号名="情绪织者_共振效果触发",
                共振类型="恐惧",
            )

    # ---------------------------- 信号：触发绝望共振 ----------------------------
    def on_情绪织者_触发绝望共振(self, 事件源实体, 事件源GUID, 信号来源实体):
        """触发绝望共振：消耗绝望值，对范围内敌人施加攻击力降低效果。"""
        自身实体: "实体" = 获取自身实体(self.game)
        情绪共振消耗: "整数" = 获取节点图变量(self.game, 变量名="情绪共振消耗")

        当前绝望: "整数" = 获取自定义变量(self.game, 目标实体=自身实体, 变量名="绝望值")
        可以触发: "布尔值" = 数值大于等于(self.game, 左值=当前绝望, 右值=情绪共振消耗)

        if 可以触发:
            # 消耗绝望值
            剩余绝望: "整数" = 减法运算(self.game, 左值=当前绝望, 右值=情绪共振消耗)
            设置自定义变量(self.game, 目标实体=自身实体, 变量名="绝望值", 变量值=剩余绝望, 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_当前绝望值", 变量值=剩余绝望, 是否触发事件=False)
            设置节点图变量(self.game, 变量名="调试_最近触发共振", 变量值="绝望共振", 是否触发事件=False)

            # 发送信号通知效果触发
            发送信号(
                self.game,
                信号名="情绪织者_共振效果触发",
                共振类型="绝望",
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
            "定时器触发时",
            self.on_定时器触发时,
            owner=self.owner_entity,
        )
        self.game.register_event_handler(
            "情绪织者_触发愤怒共振",
            self.on_情绪织者_触发愤怒共振,
            owner=self.owner_entity,
        )
        self.game.register_event_handler(
            "情绪织者_触发恐惧共振",
            self.on_情绪织者_触发恐惧共振,
            owner=self.owner_entity,
        )
        self.game.register_event_handler(
            "情绪织者_触发绝望共振",
            self.on_情绪织者_触发绝望共振,
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
