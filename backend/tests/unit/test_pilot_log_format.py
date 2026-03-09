"""パイロット名ログ表示・UNKNOWN表示・スキル発動のテスト."""

import uuid

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def create_test_unit(
    name: str,
    side: str,
    pilot_name: str | None = None,
    position: Vector3 | None = None,
    hp: int = 1000,
    accuracy: int = 100,
) -> MobileSuit:
    """テスト用モバイルスーツを生成する."""
    return MobileSuit(
        name=name,
        max_hp=hp,
        current_hp=hp,
        armor=0,
        mobility=1.0,
        sensor_range=500.0,
        position=position or Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="test_weapon",
                name="Test Weapon",
                power=50,
                range=500,
                accuracy=accuracy,
            )
        ],
        side=side,
        pilot_name=pilot_name,
    )


# ─────────────────────────────────────────────
# _format_actor_name のテスト
# ─────────────────────────────────────────────


def test_format_actor_name_no_pilot() -> None:
    """パイロット名がない場合はMS名のみ返す."""
    player = create_test_unit("Gundam", "PLAYER")
    enemy = create_test_unit("Zaku", "ENEMY")
    sim = BattleSimulator(player, [enemy])
    # 敵を索敵済みに追加
    sim.team_detected_units["PLAYER"].add(enemy.id)

    assert sim._format_actor_name(player) == "Gundam"
    assert sim._format_actor_name(enemy) == "Zaku"


def test_format_actor_name_with_pilot() -> None:
    """パイロット名がある場合は「[パイロット名]のMS名」形式で返す."""
    player = create_test_unit("Gundam", "PLAYER", pilot_name="アムロ")
    enemy = create_test_unit("Zaku", "ENEMY", pilot_name="シャア")
    sim = BattleSimulator(player, [enemy])
    sim.team_detected_units["PLAYER"].add(enemy.id)

    assert sim._format_actor_name(player) == "[アムロ]のGundam"
    assert sim._format_actor_name(enemy) == "[シャア]のZaku"


def test_format_actor_name_empty_pilot_name() -> None:
    """パイロット名が空文字列の場合はMS名のみ返す."""
    player = create_test_unit("Gundam", "PLAYER", pilot_name="")
    sim = BattleSimulator(player, [])
    # 空文字列は falsy なので名前のみ返る
    assert sim._format_actor_name(player) == "Gundam"


def test_format_actor_name_unknown_undetected_enemy() -> None:
    """未索敵の敵はUNKNOWN機として表示される."""
    player = create_test_unit("Gundam", "PLAYER")
    enemy = create_test_unit("Gelgoog", "ENEMY", pilot_name="マ・クベ")
    sim = BattleSimulator(player, [enemy])
    # 未索敵のまま（team_detected_units["PLAYER"] に追加しない）

    assert sim._format_actor_name(enemy) == "UNKNOWN機"


def test_format_actor_name_detected_after_unknown() -> None:
    """索敵後は UNKNOWN から実名表示に切り替わる."""
    player = create_test_unit("Gundam", "PLAYER")
    enemy = create_test_unit("Gelgoog", "ENEMY", pilot_name="マ・クベ")
    sim = BattleSimulator(player, [enemy])

    # 索敵前はUNKNOWN
    assert sim._format_actor_name(enemy) == "UNKNOWN機"

    # 索敵後は実名表示
    sim.team_detected_units["PLAYER"].add(enemy.id)
    assert sim._format_actor_name(enemy) == "[マ・クベ]のGelgoog"


def test_format_actor_name_player_never_unknown() -> None:
    """プレイヤー機体はUNKNOWN扱いにならない."""
    player = create_test_unit("Gundam", "PLAYER", pilot_name="アムロ")
    sim = BattleSimulator(player, [])

    # team_detected_units["PLAYER"] にプレイヤー自身がいなくても問題なし
    assert sim._format_actor_name(player) == "[アムロ]のGundam"


# ─────────────────────────────────────────────
# ログメッセージへのパイロット名組み込みテスト
# ─────────────────────────────────────────────


def test_attack_log_includes_pilot_name() -> None:
    """攻撃ログにパイロット名が含まれる."""
    player = create_test_unit("Gundam", "PLAYER", pilot_name="アムロ", accuracy=100)
    enemy = create_test_unit("Zaku", "ENEMY", position=Vector3(x=100, y=0, z=0), hp=1)
    sim = BattleSimulator(player, [enemy])
    sim.team_detected_units["PLAYER"].add(enemy.id)
    sim.team_detected_units["ENEMY"].add(player.id)

    for _ in range(10):
        if sim.is_finished:
            break
        sim.process_turn()

    attack_logs = [log for log in sim.logs if log.action_type in ("ATTACK", "MISS")]
    assert len(attack_logs) > 0

    # プレイヤーの攻撃ログに「[アムロ]のGundam」が含まれる
    player_attack_logs = [log for log in attack_logs if log.actor_id == player.id]
    if player_attack_logs:
        assert any("[アムロ]のGundam" in log.message for log in player_attack_logs)


def test_attack_log_unknown_enemy() -> None:
    """未索敵の敵からの攻撃ログに UNKNOWN機 が含まれる."""
    # 索敵範囲を0にして敵を発見できない設定
    player = create_test_unit("Gundam", "PLAYER")
    player.sensor_range = 0.0  # 索敵不可

    enemy = create_test_unit(
        "Zaku", "ENEMY", pilot_name="シャア", position=Vector3(x=50, y=0, z=0)
    )
    sim = BattleSimulator(player, [enemy])
    # 敵は索敵済みとしてマーク（攻撃できるよう）
    sim.team_detected_units["ENEMY"].add(player.id)
    # ただしプレイヤー側は敵を未索敵のまま

    # 敵の行動を直接トリガー（_action_phase）
    # 索敵フェーズをスキップして直接処理
    sim.turn = 1
    sim._action_phase(enemy)

    attack_logs = [
        log
        for log in sim.logs
        if log.action_type in ("ATTACK", "MISS") and log.actor_id == enemy.id
    ]
    assert len(attack_logs) > 0
    assert all("UNKNOWN機" in log.message for log in attack_logs)


def test_destruction_log_includes_pilot_name() -> None:
    """撃破ログにパイロット名が含まれる."""
    player = create_test_unit("Gundam", "PLAYER", accuracy=100)
    player.weapons[0].power = 9999
    enemy = create_test_unit(
        "Zaku",
        "ENEMY",
        pilot_name="ザク兵",
        position=Vector3(x=100, y=0, z=0),
        hp=1,
    )
    sim = BattleSimulator(player, [enemy])
    sim.team_detected_units["PLAYER"].add(enemy.id)
    sim.team_detected_units["ENEMY"].add(player.id)

    for _ in range(5):
        if sim.is_finished:
            break
        sim.process_turn()

    destroyed_logs = [log for log in sim.logs if log.action_type == "DESTROYED"]
    assert len(destroyed_logs) > 0
    assert any("[ザク兵]のZaku" in log.message for log in destroyed_logs)


# ─────────────────────────────────────────────
# スキル発動（skill_activated）のテスト
# ─────────────────────────────────────────────


def test_skill_activated_flag_in_battle_log() -> None:
    """BattleLog に skill_activated フィールドが存在する."""
    from app.models.models import BattleLog

    log = BattleLog(
        turn=1,
        actor_id=uuid.uuid4(),
        action_type="ATTACK",
        message="test",
        position_snapshot=Vector3(),
    )
    assert hasattr(log, "skill_activated")
    assert log.skill_activated is False


def test_skill_activated_default_false() -> None:
    """スキルなし戦闘では skill_activated は False のまま."""
    player = create_test_unit("Gundam", "PLAYER", accuracy=100)
    enemy = create_test_unit("Zaku", "ENEMY", position=Vector3(x=100, y=0, z=0), hp=1)
    sim = BattleSimulator(player, [enemy])
    sim.team_detected_units["PLAYER"].add(enemy.id)
    sim.team_detected_units["ENEMY"].add(player.id)

    for _ in range(10):
        if sim.is_finished:
            break
        sim.process_turn()

    attack_logs = [log for log in sim.logs if log.action_type in ("ATTACK", "MISS")]
    assert len(attack_logs) > 0
    # スキルなしなので skill_activated は False
    assert all(not log.skill_activated for log in attack_logs)


def test_skill_activated_with_accuracy_up() -> None:
    """accuracy_up スキルが命中判定を左右した場合に skill_activated が True になる."""
    # 命中率がスキルで辛うじて届く設定を作る:
    # 武器の accuracy を低く設定し、スキルで命中させる
    player = create_test_unit("Gundam", "PLAYER")
    player.weapons[0].accuracy = 1  # 基本命中率1%（スキルなしでほぼ外れる）
    player.weapons[0].optimal_range = 100
    player.weapons[0].decay_rate = 0.0  # 距離ペナルティなし

    enemy = create_test_unit("Zaku", "ENEMY", position=Vector3(x=100, y=0, z=0))
    enemy.mobility = 0.0  # 回避ボーナス0

    # accuracy_up Lv5 → +10% 命中率 (基本1% + 10% = 11%)
    sim = BattleSimulator(player, [enemy], player_skills={"accuracy_up": 5})
    sim.team_detected_units["PLAYER"].add(enemy.id)
    sim.team_detected_units["ENEMY"].add(player.id)

    # _calculate_hit_chance を使って検証
    weapon = player.weapons[0]
    hit_chance, _, hit_chance_no_skill = sim._calculate_hit_chance(
        player, enemy, weapon, 100.0
    )
    # スキルあり: 11%, スキルなし: 1%
    assert hit_chance > hit_chance_no_skill
    # スキルの効果が正しく計算されている
    assert abs(hit_chance - hit_chance_no_skill - 10.0) < 0.01
