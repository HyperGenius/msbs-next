"""Tests for weapon slot -> role mapping (Issue #502)."""

from app.engine.constants import (
    WEAPON_SLOT_ROLE_LEFT_ARM,
    WEAPON_SLOT_ROLE_RACK,
    WEAPON_SLOT_ROLE_RIGHT_ARM,
    get_weapon_slot_role,
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
