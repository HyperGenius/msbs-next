"""Tests for Phase 6-4: Probabilistic Detection (Distance-Dependent Detection Probability).

距離依存発見確率の導入を検証する。
- 距離 0m で発見確率 100%、effective_sensor_range で 0%
- 既発見ユニットへの確率判定スキップ（LOS チェックのみ）
- ミノフスキー粒子時に DETECTION_FALLOFF_EXPONENT_MINOVSKY が使われること
- 発見ログに索敵確率パーセントが含まれること
"""

from unittest.mock import patch

from app.engine.constants import (
    DETECTION_FALLOFF_EXPONENT,
    DETECTION_FALLOFF_EXPONENT_MINOVSKY,
    SPECIAL_ENVIRONMENT_EFFECTS,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

_MINOVSKY_SENSOR_MULTIPLIER = SPECIAL_ENVIRONMENT_EFFECTS["MINOVSKY"][
    "sensor_range_multiplier"
]


def _make_ms(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    sensor_range: float = 500.0,
    max_hp: int = 100,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=max_hp,
        armor=5,
        mobility=1.0,
        sensor_range=sensor_range,
        position=position,
        weapons=[
            Weapon(
                id="beam_rifle",
                name="Beam Rifle",
                power=20,
                range=600,
                accuracy=80,
            )
        ],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )


# ---------------------------------------------------------------------------
# 定数テスト
# ---------------------------------------------------------------------------


def test_detection_falloff_exponent_constants() -> None:
    """DETECTION_FALLOFF_EXPONENT と DETECTION_FALLOFF_EXPONENT_MINOVSKY が正しい値であることをテスト."""
    assert DETECTION_FALLOFF_EXPONENT == 2.0
    assert DETECTION_FALLOFF_EXPONENT_MINOVSKY == 3.0


# ---------------------------------------------------------------------------
# 発見確率の境界値テスト
# ---------------------------------------------------------------------------


def test_detection_probability_at_zero_distance() -> None:
    """距離 0m では発見確率 100%（常に発見）であることをテスト."""
    # 距離 0m: ratio=0, prob=max(0, 1-0^2)=1.0 → 常に発見
    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=500.0)
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=0, y=0, z=0), sensor_range=500.0)

    sim = BattleSimulator(player, [enemy], environment="SPACE")
    # random.random() が最大値 (0.9999) でも prob=1.0 なので常に発見
    with patch("app.engine.targeting.random.random", return_value=0.9999):
        sim._detection_phase()

    assert enemy.id in sim.team_detected_units["PLAYER_TEAM"]


def test_detection_probability_at_effective_range() -> None:
    """effective_sensor_range ちょうどでは発見確率 0%（発見不可）であることをテスト."""
    sensor_range = 500.0
    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=sensor_range)
    # ちょうど sensor_range の距離に配置
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=sensor_range, y=0, z=0))

    sim = BattleSimulator(player, [enemy], environment="SPACE")
    # ratio = 500/500 = 1.0, prob = max(0, 1-1^2) = 0 → 発見不可
    # random.random() の値に関わらず発見されない
    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()

    assert enemy.id not in sim.team_detected_units["PLAYER_TEAM"]


def test_detection_probability_outside_sensor_range() -> None:
    """effective_sensor_range 外では発見されないことをテスト."""
    sensor_range = 500.0
    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=sensor_range)
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=sensor_range + 1.0, y=0, z=0))

    sim = BattleSimulator(player, [enemy], environment="SPACE")
    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()

    assert enemy.id not in sim.team_detected_units["PLAYER_TEAM"]


def test_detection_succeeds_when_random_below_prob() -> None:
    """random() が detect_prob 未満の場合に発見が成功することをテスト."""
    sensor_range = 500.0
    distance = 250.0  # ratio=0.5, prob=max(0,1-0.5^2)=0.75
    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=sensor_range)
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=distance, y=0, z=0))

    sim = BattleSimulator(player, [enemy], environment="SPACE")
    with patch("app.engine.targeting.random.random", return_value=0.74):
        sim._detection_phase()

    assert enemy.id in sim.team_detected_units["PLAYER_TEAM"]


def test_detection_fails_when_random_above_prob() -> None:
    """random() が detect_prob 以上の場合に発見が失敗することをテスト."""
    sensor_range = 500.0
    distance = 250.0  # ratio=0.5, prob=max(0,1-0.5^2)=0.75
    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=sensor_range)
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=distance, y=0, z=0))

    sim = BattleSimulator(player, [enemy], environment="SPACE")
    with patch("app.engine.targeting.random.random", return_value=0.75):
        sim._detection_phase()

    assert enemy.id not in sim.team_detected_units["PLAYER_TEAM"]


# ---------------------------------------------------------------------------
# 発見の永続性テスト（既発見ユニットへの確率判定スキップ）
# ---------------------------------------------------------------------------


def test_already_detected_skips_probability_check() -> None:
    """既に発見済みのユニットへは確率判定がスキップされることをテスト."""
    sensor_range = 500.0
    distance = 250.0  # prob=0.75
    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=sensor_range)
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=distance, y=0, z=0))

    sim = BattleSimulator(player, [enemy], environment="SPACE")
    # 手動で発見済みにする
    sim.team_detected_units["PLAYER_TEAM"].add(enemy.id)

    # random.random() が高い値（確率判定なら失敗する値）でも、既発見なので維持される
    with patch("app.engine.targeting.random.random", return_value=0.99):
        sim._detection_phase()

    # 障害物なしの場合、既発見ユニットは発見済みリストから除外されない
    assert enemy.id in sim.team_detected_units["PLAYER_TEAM"]


# ---------------------------------------------------------------------------
# ミノフスキー粒子テスト（強化された減衰指数）
# ---------------------------------------------------------------------------


def test_minovsky_uses_higher_falloff_exponent() -> None:
    """ミノフスキー粒子時は DETECTION_FALLOFF_EXPONENT_MINOVSKY が使われ、
    同距離での発見確率が通常より低いことをテスト."""
    sensor_range = 600.0
    distance = 200.0

    # 通常時: effective_range=600, ratio=200/600≈0.333, prob=1-0.333^2≈0.889
    normal_ratio = distance / sensor_range
    normal_prob = max(0.0, 1.0 - normal_ratio ** DETECTION_FALLOFF_EXPONENT)

    # ミノフスキー粒子時: effective_range=600*0.5=300, ratio=200/300≈0.667
    # falloff=DETECTION_FALLOFF_EXPONENT_MINOVSKY=3.0
    minovsky_effective = sensor_range * _MINOVSKY_SENSOR_MULTIPLIER
    minovsky_ratio = distance / minovsky_effective
    minovsky_prob = max(0.0, 1.0 - minovsky_ratio ** DETECTION_FALLOFF_EXPONENT_MINOVSKY)

    # ミノフスキー粒子下の方が確率が低いはず
    assert minovsky_prob < normal_prob


def test_minovsky_detection_with_high_exponent() -> None:
    """ミノフスキー粒子時の発見確率判定が DETECTION_FALLOFF_EXPONENT_MINOVSKY を使用することをテスト."""
    sensor_range = 600.0
    distance = 200.0
    # ミノフスキー粒子: effective=300m, ratio=200/300≈0.667
    # prob = 1 - 0.667^3 ≈ 0.704
    minovsky_effective = sensor_range * _MINOVSKY_SENSOR_MULTIPLIER
    ratio = distance / minovsky_effective
    minovsky_prob = max(0.0, 1.0 - ratio ** DETECTION_FALLOFF_EXPONENT_MINOVSKY)

    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=sensor_range)
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=distance, y=0, z=0))

    # random.random() が minovsky_prob 未満 → 発見成功
    sim_detect = BattleSimulator(
        player, [enemy], environment="SPACE", special_effects=["MINOVSKY"]
    )
    with patch("app.engine.targeting.random.random", return_value=minovsky_prob - 0.01):
        sim_detect._detection_phase()
    assert enemy.id in sim_detect.team_detected_units["PLAYER_TEAM"]

    # random.random() が minovsky_prob 以上 → 発見失敗
    player2 = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=sensor_range)
    enemy2 = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=distance, y=0, z=0))
    sim_miss = BattleSimulator(
        player2, [enemy2], environment="SPACE", special_effects=["MINOVSKY"]
    )
    with patch("app.engine.targeting.random.random", return_value=minovsky_prob + 0.01):
        sim_miss._detection_phase()
    assert enemy2.id not in sim_miss.team_detected_units["PLAYER_TEAM"]


# ---------------------------------------------------------------------------
# 発見ログに確率値が含まれることをテスト
# ---------------------------------------------------------------------------


def test_detection_log_includes_probability_percentage() -> None:
    """発見ログに「索敵確率 XX%」が含まれることをテスト."""
    sensor_range = 500.0
    distance = 100.0  # ratio=0.2, prob=max(0,1-0.04)=0.96 → 96%
    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=sensor_range)
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=distance, y=0, z=0))

    sim = BattleSimulator(player, [enemy], environment="SPACE")
    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()

    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    assert len(detection_logs) >= 1
    assert any("索敵確率" in log.message for log in detection_logs)
    assert any("%" in log.message for log in detection_logs)


def test_minovsky_detection_log_includes_probability_percentage() -> None:
    """ミノフスキー粒子時の発見ログにも「索敵確率 XX%」が含まれることをテスト."""
    sensor_range = 600.0
    distance = 100.0
    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM", Vector3(x=0, y=0, z=0), sensor_range=sensor_range)
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM", Vector3(x=distance, y=0, z=0))

    sim = BattleSimulator(
        player, [enemy], environment="SPACE", special_effects=["MINOVSKY"]
    )
    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()

    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    assert len(detection_logs) >= 1
    assert any("ミノフスキー粒子" in log.message for log in detection_logs)
    assert any("索敵確率" in log.message for log in detection_logs)
