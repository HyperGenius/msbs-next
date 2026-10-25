# backend/app/services/retreat_support_mission.py
"""撤退支援の作戦マスター（Epic #682 Sub-Issue 4、Issue #686）.

損傷した友軍を撤退ポイントまで逃がし、追ってくる敵小隊から守る。
DB への投入は `scripts/maintenance/upsert_retreat_support_mission.py`。
"""

from app.engine.constants import (
    UNIT_ROLE_SNIPER,
    UNIT_ROLE_VANGUARD,
    UNIT_ROLE_WITHDRAW,
)
from app.models.models import (
    MISSION_OBJECTIVE_RETREAT_SUPPORT,
    MISSION_TEAM_ENEMY,
    MISSION_TEAM_PLAYER,
    Mission,
    MissionLayout,
    MissionUnitConfig,
    RetreatPoint,
    SpawnZone,
    Vector3,
)

RETREAT_SUPPORT_MISSION_ID = 4
RETREAT_SUPPORT_REQUIRED = 2
"""成功に必要な離脱数。友軍は 3 機。"""
FIELD_SIZE = 4000.0
ALLY_MAX_SPEED = 35.0
"""撤退機の最高速度 (m/s)。追撃部隊（既定の 80 m/s）に追いつかれる速さにする。"""

DESCRIPTION = (
    "損傷した友軍 3 機を撤退ポイントまで逃がせ。友軍は撃ち返せない。"
    "2 機以上が離脱すれば成功、3 機とも逃がせば報酬が増える。"
    "追撃部隊は格闘機 1 機・前衛 1 機・狙撃機 2 機。敵を全滅させなくてもよい。"
    "撤退機を狙う敵を射程の外から撃ち、狙いを自機に引きつけろ。"
)


ALLY_MASTER_ID = "gm"
"""撤退機の機体マスター。"""
MELEE_VANGUARD_MASTER_ID = "gouf"
"""追撃部隊の 1 小隊目の前衛の機体マスター。格闘武器（ヒートロッド）を持つ。

格闘機は 1 機だけにする。2 機にすると、プレイヤー機を落としてから撤退機を追う。
そうなると、どのビルドでもほぼ成功しない。
"""
VANGUARD_MASTER_ID = "zaku_ii"
"""追撃部隊の 2 小隊目の前衛の機体マスター。"""
SNIPER_MASTER_ID = "zaku_ii"
"""追撃部隊の後衛の機体マスター。

追撃部隊の射撃武器より射程の長い武器で撃つと、有利になる。
ゲルググ（射程の長いビームライフル）にすると、どのビルドでもほぼ成功しない。
"""


def _ally(index: int, hp_ratio: float, missing_parts: list[str]) -> MissionUnitConfig:
    return MissionUnitConfig(
        master_mobile_suit_id=ALLY_MASTER_ID,
        name=f"撤退機 #{index}",
        current_hp_ratio=hp_ratio,
        missing_parts=missing_parts,
        max_speed=ALLY_MAX_SPEED,
        hold_fire=True,
        role=UNIT_ROLE_WITHDRAW,
        squad_id="retreat",
    )


def _pursuit_squad(index: int) -> str:
    """追撃部隊の小隊 ID. 同じ番号の前衛と狙撃機で 1 小隊を組む."""
    return f"pursuit-{index}"


def _pursuer_vanguard(index: int, master_id: str, name: str) -> MissionUnitConfig:
    return MissionUnitConfig(
        master_mobile_suit_id=master_id,
        name=name,
        role=UNIT_ROLE_VANGUARD,
        squad_id=_pursuit_squad(index),
    )


def _pursuer_sniper(index: int) -> MissionUnitConfig:
    return MissionUnitConfig(
        master_mobile_suit_id=SNIPER_MASTER_ID,
        name=f"追撃狙撃機 #{index}",
        role=UNIT_ROLE_SNIPER,
        squad_id=_pursuit_squad(index),
    )


def _unit_config_json(config: MissionUnitConfig) -> dict:
    # 機体マスターを参照する機体に、使わない直書きの値を残さない。
    return config.model_dump(mode="json", exclude_defaults=True)


def build_retreat_support_mission() -> Mission:
    """撤退支援の作戦マスターを組み立てる（DB には入れない）."""
    allies = [
        _ally(1, 0.4, ["LEFT_ARM"]),
        _ally(2, 0.55, []),
        _ally(3, 0.35, ["RIGHT_LEG"]),
    ]
    enemies = [
        _pursuer_vanguard(1, MELEE_VANGUARD_MASTER_ID, "追撃格闘機"),
        _pursuer_vanguard(2, VANGUARD_MASTER_ID, "追撃前衛機"),
        _pursuer_sniper(1),
        _pursuer_sniper(2),
    ]
    # 撤退ポイントまで約 2400m。撤退機の速さで 70 秒ほどかかる。
    # 追撃部隊は、狙撃機の射程と索敵範囲の外から追い始める。
    mid = FIELD_SIZE / 2
    layout = MissionLayout(
        field_size=FIELD_SIZE,
        spawn_zones=[
            SpawnZone(
                team_id=MISSION_TEAM_PLAYER,
                center=Vector3(x=2800, y=0, z=mid),
                radius=150,
            ),
            SpawnZone(
                team_id=MISSION_TEAM_ENEMY,
                center=Vector3(x=3700, y=0, z=mid),
                radius=100,
            ),
        ],
        retreat_points=[
            RetreatPoint(
                position=Vector3(x=300, y=0, z=mid),
                radius=120,
                team_id=MISSION_TEAM_PLAYER,
            )
        ],
    )
    return Mission(
        id=RETREAT_SUPPORT_MISSION_ID,
        name="撤退支援",
        difficulty=2,
        description=DESCRIPTION,
        environment="SPACE",
        enemy_config={"enemies": [_unit_config_json(e) for e in enemies]},
        objective={
            "type": MISSION_OBJECTIVE_RETREAT_SUPPORT,
            "params": {"required": RETREAT_SUPPORT_REQUIRED},
        },
        allies_config=[_unit_config_json(a) for a in allies],
        layout=layout.model_dump(mode="json"),
        is_active=True,
    )
