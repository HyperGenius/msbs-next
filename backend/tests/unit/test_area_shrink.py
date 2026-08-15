"""Tests for Issue #474 — Area Shrink Mechanics.

Validates:
1. constants: SHRINK_* / MIN_SHRUNK_FIELD_SIZE が定義されていること
2. SHRINK_START_STEP に到達するまでは map_bounds が変化しないこと
3. SHRINK_START_STEP 以降、SHRINK_INTERVAL_STEPS ごとに map_bounds が収縮すること
4. 収縮が固定中心を基準に対称に行われること
5. MIN_SHRUNK_FIELD_SIZE を下回らないこと
6. いずれかのチームの生存数が SHRINK_PAUSE_ALIVE_THRESHOLD 以下になったら収縮が停止すること
7. 収縮イベントが BattleLog に記録されること（毎ステップではなくイベント単位）
"""

from __future__ import annotations

from app.engine.constants import (
    MIN_SHRUNK_FIELD_SIZE,
    SHRINK_INTERVAL_STEPS,
    SHRINK_PAUSE_ALIVE_THRESHOLD,
    SHRINK_RATIO,
    SHRINK_START_STEP,
)
from app.engine.simulation import BattleSimulator
from app.models.models import BattleField, MobileSuit, Vector3, Weapon


def _make_weapon(range_: float = 500.0, power: int = 30) -> Weapon:
    return Weapon(
        id=f"w_{id(object())}",
        name="Test Weapon",
        power=power,
        range=range_,
        accuracy=80.0,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    current_hp: int = 100,
    max_hp: int = 100,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=current_hp,
        armor=0,
        mobility=1.0,
        position=Vector3(x=0, y=0, z=0),
        sensor_range=500.0,
        side=side,
        team_id=team_id,
        weapons=[_make_weapon()],
    )


def _make_large_sim(n_per_team: int = 20) -> BattleSimulator:
    """収縮の余地が十分にある大きめのフィールドを持つシミュレータを作る.

    ステップ経過中に決着してしまうと収縮ロジックを検証できないため、HPを
    大きく確保して SHRINK_START_STEP 以降まで両チームとも全滅しないようにする。
    """
    player = _make_unit("P", "PLAYER", "PT", current_hp=1_000_000, max_hp=1_000_000)
    enemies = [
        _make_unit(f"E{i}", "ENEMY", "ET", current_hp=1_000_000, max_hp=1_000_000)
        for i in range(n_per_team - 1)
    ]
    return BattleSimulator(
        player, enemies, battlefield=BattleField(obstacle_density="NONE")
    )


# ---------------------------------------------------------------------------
# 1. 定数定義テスト
# ---------------------------------------------------------------------------


def test_shrink_constants_defined() -> None:
    """収縮関連の定数が定義されていること."""
    assert SHRINK_START_STEP > 0
    assert SHRINK_INTERVAL_STEPS > 0
    assert 0.0 < SHRINK_RATIO < 1.0
    assert MIN_SHRUNK_FIELD_SIZE > 0
    assert SHRINK_PAUSE_ALIVE_THRESHOLD >= 0


# ---------------------------------------------------------------------------
# 2. SHRINK_START_STEP までは収縮しないこと
# ---------------------------------------------------------------------------


def test_map_bounds_unchanged_before_shrink_start() -> None:
    """SHRINK_START_STEP に到達するまでは map_bounds が変化しないこと."""
    sim = _make_large_sim()
    original_bounds = sim.map_bounds

    for _ in range(SHRINK_START_STEP - 1):
        sim.step()

    assert sim.map_bounds == original_bounds


# ---------------------------------------------------------------------------
# 3. SHRINK_START_STEP 以降、段階的に収縮すること
# ---------------------------------------------------------------------------


def test_map_bounds_shrinks_after_start_step() -> None:
    """SHRINK_START_STEP 到達後、最初の収縮イベントで辺長が SHRINK_RATIO 倍になること."""
    sim = _make_large_sim()
    original_min, original_max = sim.map_bounds
    original_side_len = original_max - original_min

    for _ in range(SHRINK_START_STEP + 1):
        sim.step()

    new_min, new_max = sim.map_bounds
    new_side_len = new_max - new_min
    assert new_side_len < original_side_len
    expected_side_len = max(MIN_SHRUNK_FIELD_SIZE, original_side_len * SHRINK_RATIO)
    assert abs(new_side_len - expected_side_len) < 1e-6


def test_map_bounds_shrinks_again_after_second_interval() -> None:
    """2回目の収縮イベントでさらに辺長が SHRINK_RATIO 倍になること."""
    sim = _make_large_sim()
    original_min, original_max = sim.map_bounds
    original_side_len = original_max - original_min

    for _ in range(SHRINK_START_STEP + SHRINK_INTERVAL_STEPS + 1):
        sim.step()

    _, _ = sim.map_bounds
    new_side_len = sim.map_bounds[1] - sim.map_bounds[0]
    expected_side_len = max(
        MIN_SHRUNK_FIELD_SIZE, original_side_len * (SHRINK_RATIO**2)
    )
    assert abs(new_side_len - expected_side_len) < 1e-6


# ---------------------------------------------------------------------------
# 4. 固定中心を基準に対称であること
# ---------------------------------------------------------------------------


def test_shrink_is_symmetric_around_fixed_center() -> None:
    """収縮が固定中心を基準に対称に行われること."""
    sim = _make_large_sim()
    center = sim._map_center

    for _ in range(SHRINK_START_STEP + 1):
        sim.step()

    new_min, new_max = sim.map_bounds
    assert abs((new_min + new_max) / 2.0 - center) < 1e-6


# ---------------------------------------------------------------------------
# 5. MIN_SHRUNK_FIELD_SIZE を下回らないこと
# ---------------------------------------------------------------------------


def test_map_bounds_never_below_min_shrunk_field_size() -> None:
    """多数の収縮間隔を経過させても MIN_SHRUNK_FIELD_SIZE を下回らないこと."""
    sim = _make_large_sim()

    # 十分な回数の収縮間隔が経過するまでステップを進める
    total_steps = SHRINK_START_STEP + SHRINK_INTERVAL_STEPS * 30
    for _ in range(total_steps):
        if sim.is_finished:
            break
        sim.step()

    side_len = sim.map_bounds[1] - sim.map_bounds[0]
    assert side_len >= MIN_SHRUNK_FIELD_SIZE - 1e-6


# ---------------------------------------------------------------------------
# 6. 残存数が少ない場合に収縮が停止すること
# ---------------------------------------------------------------------------


def test_shrink_pauses_when_team_depleted_from_larger_start() -> None:
    """開始時3機だったチームが1機まで消耗した場合は収縮が停止すること.

    1vs1ソロミッションのように「開始時点からチーム人数が
    SHRINK_PAUSE_ALIVE_THRESHOLD 以下」のケースは意図的に対象外とする
    （そうしないとソロミッションで収縮が一切発動しなくなるため）。
    ここでは開始時3機だったチームが2機撃破され1機まで消耗した状況を
    直接構築し、消耗によるチームのみが停止判定の対象になることを確認する。
    """
    player = _make_unit("P", "PLAYER", "PT", current_hp=1_000_000, max_hp=1_000_000)
    fallen_ally_1 = _make_unit("A1", "PLAYER", "PT", current_hp=0)
    fallen_ally_2 = _make_unit("A2", "PLAYER", "PT", current_hp=0)
    enemy = _make_unit("E", "ENEMY", "ET", current_hp=1_000_000, max_hp=1_000_000)
    sim = BattleSimulator(
        player,
        [fallen_ally_1, fallen_ally_2, enemy],
        battlefield=BattleField(obstacle_density="NONE"),
    )
    original_bounds = sim.map_bounds

    for _ in range(SHRINK_START_STEP + SHRINK_INTERVAL_STEPS * 3):
        if sim.is_finished:
            break
        sim.step()

    assert sim.map_bounds == original_bounds
    assert sim._shrink_paused is True


def test_shrink_not_paused_for_1v1_from_start() -> None:
    """1vs1ソロミッションでは開始時点からチーム人数が1でも収縮が発動すること."""
    player = _make_unit("P", "PLAYER", "PT", current_hp=1_000_000, max_hp=1_000_000)
    enemy = _make_unit("E", "ENEMY", "ET", current_hp=1_000_000, max_hp=1_000_000)
    sim = BattleSimulator(
        player, [enemy], battlefield=BattleField(obstacle_density="NONE")
    )
    original_bounds = sim.map_bounds

    for _ in range(SHRINK_START_STEP + 1):
        if sim.is_finished:
            break
        sim.step()

    assert sim.map_bounds != original_bounds
    assert sim._shrink_paused is False


# ---------------------------------------------------------------------------
# 7. BattleLog にイベント単位で記録されること
# ---------------------------------------------------------------------------


def test_area_shrink_event_logged() -> None:
    """収縮イベントが BattleLog に記録されること."""
    sim = _make_large_sim()

    for _ in range(SHRINK_START_STEP + 1):
        sim.step()

    shrink_logs = [log for log in sim.logs if log.action_type == "AREA_SHRINK"]
    assert len(shrink_logs) == 1
    log = shrink_logs[0]
    assert log.details is not None
    assert log.details["reason"] == "scheduled_shrink"
    assert log.details["step"] == SHRINK_START_STEP


def test_area_shrink_pause_logged_once() -> None:
    """収縮停止イベントが重複せず一度だけ記録されること."""
    player = _make_unit("P", "PLAYER", "PT", current_hp=1_000_000, max_hp=1_000_000)
    fallen_ally_1 = _make_unit("A1", "PLAYER", "PT", current_hp=0)
    fallen_ally_2 = _make_unit("A2", "PLAYER", "PT", current_hp=0)
    enemy = _make_unit("E", "ENEMY", "ET", current_hp=1_000_000, max_hp=1_000_000)
    sim = BattleSimulator(
        player,
        [fallen_ally_1, fallen_ally_2, enemy],
        battlefield=BattleField(obstacle_density="NONE"),
    )

    for _ in range(SHRINK_START_STEP + SHRINK_INTERVAL_STEPS * 3):
        if sim.is_finished:
            break
        sim.step()

    pause_logs = [
        log
        for log in sim.logs
        if log.action_type == "AREA_SHRINK"
        and log.details is not None
        and log.details["reason"] == "paused_low_survivors"
    ]
    assert len(pause_logs) == 1
