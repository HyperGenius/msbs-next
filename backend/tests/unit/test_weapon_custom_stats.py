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


def test_apply_effective_spec_with_none_custom_stats_returns_base_values() -> None:
    """custom_stats が None（DB上のnullable列由来）の場合も空 {} と同様に扱われる."""
    weapon = WeaponService.apply_effective_spec(BASE_SNAPSHOT, None)

    assert weapon.power == 50
    assert weapon.accuracy == 80.0


def test_apply_effective_spec_without_aim_distribution_override_uses_base_default() -> (
    None
):
    """custom_stats に aim_distribution が無い場合、base_snapshot側(未設定ならデフォルト値)を使う (Issue #505)."""
    weapon = WeaponService.apply_effective_spec(BASE_SNAPSHOT, {})

    assert weapon.aim_distribution == {
        "TORSO": 0.5,
        "RIGHT_ARM": 0.1,
        "LEFT_ARM": 0.1,
        "RIGHT_LEG": 0.1,
        "LEFT_LEG": 0.1,
        "HEAD": 0.1,
    }


def test_apply_effective_spec_applies_aim_distribution_override() -> None:
    """custom_stats.aim_distribution が指定された場合、base_snapshotの値を上書きする (Issue #505)."""
    override = {
        "HEAD": 0.4,
        "TORSO": 0.4,
        "RIGHT_ARM": 0.05,
        "LEFT_ARM": 0.05,
        "RIGHT_LEG": 0.05,
        "LEFT_LEG": 0.05,
    }

    weapon = WeaponService.apply_effective_spec(
        BASE_SNAPSHOT, {"aim_distribution": override}
    )

    assert weapon.aim_distribution == override
