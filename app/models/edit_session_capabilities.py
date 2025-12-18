from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class EditSessionCapabilities:
    """显式的编辑会话能力集合（单一真源）。

    设计目标：
    - 将“只读 / 可交互 / 可保存 / 可校验”的语义从零散 bool 收敛到一个对象；
    - 各层（Controller / View / Scene）只允许读取该对象，不再各自猜测或拼装组合；
    - 能力组合必须自洽：可保存必然要求可校验。
    """

    can_interact: bool
    can_persist: bool
    can_validate: bool

    def __post_init__(self) -> None:
        if self.can_persist and not self.can_validate:
            raise ValueError("EditSessionCapabilities: can_persist=True 时必须同时 can_validate=True")

    @property
    def is_read_only(self) -> bool:
        """只读（禁止交互）语义：用于映射到 View/Scene 的 read_only。"""
        return not self.can_interact

    def with_overrides(
        self,
        *,
        can_interact: bool | None = None,
        can_persist: bool | None = None,
        can_validate: bool | None = None,
    ) -> "EditSessionCapabilities":
        """返回修改指定字段后的新对象（保持 frozen）。"""
        return replace(
            self,
            can_interact=self.can_interact if can_interact is None else bool(can_interact),
            can_persist=self.can_persist if can_persist is None else bool(can_persist),
            can_validate=self.can_validate if can_validate is None else bool(can_validate),
        )

    # === 推荐工厂方法（统一语义命名，避免到处手写组合） ===

    @classmethod
    def read_only_preview(cls) -> "EditSessionCapabilities":
        """只读预览：不可交互，不可保存，不可校验（上层可额外隐藏自动排版等入口）。"""
        return cls(can_interact=False, can_persist=False, can_validate=False)

    @classmethod
    def interactive_preview(cls) -> "EditSessionCapabilities":
        """可交互预览：允许交互，但不允许保存到资源落盘；允许校验（例如自动排版前校验）。"""
        return cls(can_interact=True, can_persist=False, can_validate=True)

    @classmethod
    def full_editing(cls) -> "EditSessionCapabilities":
        """完整编辑：允许交互 + 校验 + 保存。"""
        return cls(can_interact=True, can_persist=True, can_validate=True)


