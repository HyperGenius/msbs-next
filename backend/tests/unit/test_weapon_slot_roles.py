"""Tests for weapon slot -> role mapping (Issue #502, #504)."""

from app.engine.constants import (
    WEAPON_SLOT_ROLE_LEFT_ARM,
    WEAPON_SLOT_ROLE_RACK,
    WEAPON_SLOT_ROLE_RIGHT_ARM,
    get_weapon_slot_role,
    get_weapon_slot_role_for_weapon,
)
from app.models.models import Weapon


def _make_weapon(weapon_id: str) -> Weapon:
    return Weapon(
        id=weapon_id,
        name="テスト武器",
        power=100,
        range=300.0,
        accuracy=80.0,
    )


def test_slot_0_is_right_arm():
    """スロットindex 0は右腕ロールを返す."""
    assert get_weapon_slot_role(0) == WEAPON_SLOT_ROLE_RIGHT_ARM


def test_slot_1_is_left_arm():
    """スロットindex 1は左腕ロールを返す."""
    assert get_weapon_slot_role(1) == WEAPON_SLOT_ROLE_LEFT_ARM


def test_slot_2_and_beyond_is_rack():
    """スロットindex 2以降は武装ラックロールを返す."""
    assert get_weapon_slot_role(2) == WEAPON_SLOT_ROLE_RACK
    assert get_weapon_slot_role(5) == WEAPON_SLOT_ROLE_RACK


def test_get_weapon_slot_role_for_weapon_finds_role_by_id():
    """武器IDから所属スロットのindexを引いて部位ロールを返す (Issue #504)."""
    weapons = [_make_weapon("w-right"), _make_weapon("w-left")]

    assert get_weapon_slot_role_for_weapon(weapons, "w-right") == (
        WEAPON_SLOT_ROLE_RIGHT_ARM
    )
    assert get_weapon_slot_role_for_weapon(weapons, "w-left") == (
        WEAPON_SLOT_ROLE_LEFT_ARM
    )


def test_get_weapon_slot_role_for_weapon_returns_none_when_not_found():
    """`weapons` にIDが見つからない場合は None を返す (Issue #504)."""
    weapons = [_make_weapon("w-right")]

    assert get_weapon_slot_role_for_weapon(weapons, "unknown") is None
