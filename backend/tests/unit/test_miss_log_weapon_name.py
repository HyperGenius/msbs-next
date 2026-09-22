"""Issue #523: MISS ログに weapon_name/weapon_id が記録されることのテスト."""

from app.engine.simulation import BattleSimulator
from app.models.models import BattleLog, MobileSuit, Vector3, Weapon


def _make_weapon(power: int = 100, accuracy: int = 1) -> Weapon:
    return Weapon(
        id="test_beam_rifle",
        name="Test Beam Rifle",
        power=power,
        range=600.0,
        accuracy=accuracy,
        type="BEAM",
        optimal_range=300.0,
        decay_rate=0.05,
        cooldown_sec=0.0,
        max_ammo=999,
    )


def _make_unit(
    name: str,
    side: str,
    position: Vector3,
    hp: int = 1000,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=hp,
        current_hp=hp,
        armor=0,
        mobility=0.0,
        position=position,
        weapons=[_make_weapon()],
        side=side,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=0.0,
        acceleration=0.0,
        sensor_range=10000.0,
    )


def test_miss_log_records_weapon_name_and_id() -> None:
    """MISS ログに、実際に使用した武器の weapon_name/weapon_id が記録されること."""
    # 命中率(accuracy=1)を極限まで下げて MISS を確実に発生させる（射程内・最適距離）
    player = _make_unit("Player", "PLAYER", Vector3(x=-500, y=0, z=0), hp=10000)
    enemy = _make_unit("Enemy", "ENEMY", Vector3(x=0, y=0, z=0), hp=10000)

    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(enemy.id)]["body_heading_deg"] = 0.0

    max_steps = 50
    for _ in range(max_steps):
        if sim.is_finished:
            break
        sim.step()

    miss_logs: list[BattleLog] = [log for log in sim.logs if log.action_type == "MISS"]
    assert len(miss_logs) > 0, "少なくとも 1 回の MISS ログがあること"

    for log in miss_logs:
        assert log.weapon_name == "Test Beam Rifle", (
            f"MISS ログに実際の使用武器名が記録されること（実際: {log.weapon_name!r}）"
        )
        assert log.weapon_id == "test_beam_rifle", (
            f"MISS ログに実際の使用武器IDが記録されること（実際: {log.weapon_id!r}）"
        )
