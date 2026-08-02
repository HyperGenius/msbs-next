"""WeaponService.apply_effective_spec（custom_stats マージ）のユニットテスト."""

from app.services.weapon_service import WeaponService

BASE_SNAPSHOT = {
    "id": "zaku_mg",
    "name": "ザク・マシンガン",
    "power": 50,
    "range": 400.0,
    "accuracy": 80.0,
}


def test_apply_effective_spec_with_empty_custom_stats_returns_base_values() -> None:
    """custom_stats が空 {} の場合、base_snapshot の値がそのまま使われる（既存データの後方互換）."""
    weapon = WeaponService.apply_effective_spec(BASE_SNAPSHOT, {})

    assert weapon.power == 50
    assert weapon.accuracy == 80.0


def test_apply_effective_spec_applies_power_and_accuracy_bonus() -> None:
    """power_bonus / accuracy_bonus が base_snapshot の値に加算される."""
    custom_stats = {"power_bonus": 10, "accuracy_bonus": 5.0}

    weapon = WeaponService.apply_effective_spec(BASE_SNAPSHOT, custom_stats)

    assert weapon.power == 60
    assert weapon.accuracy == 85.0


def test_apply_effective_spec_ignores_missing_keys_as_zero() -> None:
    """一部のキーのみ存在する場合、欠損キーは0/未変更として扱われる."""
    weapon = WeaponService.apply_effective_spec(BASE_SNAPSHOT, {"power_bonus": 20})

    assert weapon.power == 70
    assert weapon.accuracy == 80.0
