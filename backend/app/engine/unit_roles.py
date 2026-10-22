# backend/app/engine/unit_roles.py
"""ユニットのロールと所属小隊.

ロールと小隊は戦闘ごとの割り当てなので、`MobileSuit` には持たせない。
`BattleSimulator` にユニット ID ごとに渡す。
"""

from dataclasses import dataclass

from app.engine.constants import VALID_UNIT_ROLES


@dataclass(frozen=True)
class UnitAssignment:
    """1 ユニットのロールと所属小隊."""

    role: str | None = None
    """`VALID_UNIT_ROLES` のいずれか。None はロールなし。"""
    squad_id: str | None = None
    """同じチームの中で組んで動く機体の組。None は小隊なし。"""

    def __post_init__(self) -> None:
        """ロールの値を検証する."""
        if self.role is not None and self.role not in VALID_UNIT_ROLES:
            raise ValueError(f"unknown unit role: {self.role}")
