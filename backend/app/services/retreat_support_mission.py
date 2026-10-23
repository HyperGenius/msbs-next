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
    MissionWeaponConfig,
    RetreatPoint,
    SpawnZone,
    Vector3,
)

RETREAT_SUPPORT_MISSION_ID = 4
RETREAT_SUPPORT_REQUIRED = 2
"""成功に必要な離脱数。友軍は 3 機。"""

DESCRIPTION = (
    "損傷した友軍 3 機を撤退ポイントまで逃がせ。2 機以上が離脱すれば成功、"
    "3 機とも逃がせば報酬が増える。追撃部隊は格闘機 2 機と狙撃機 2 機。"
    "敵を全滅させなくてもよい。足止め・護衛・索敵に向いた機体が有利。"
)


def _ally(index: int, current_hp: int, missing_parts: list[str]) -> MissionUnitConfig:
    return MissionUnitConfig(
        name=f"撤退機 #{index}",
        max_hp=90,
        current_hp=current_hp,
        armor=5,
        mobility=1.1,
        missing_parts=missing_parts,
        weapon=MissionWeaponConfig(
            id=f"retreat_ally_mg_{index}",
            name="ザクマシンガン",
            power=12,
            range=350,
            accuracy=60,
        ),
        role=UNIT_ROLE_WITHDRAW,
        squad_id="retreat",
    )


def _pursuit_squad(index: int) -> str:
    """追撃部隊の小隊 ID. 同じ番号の格闘機と狙撃機で 1 小隊を組む."""
    return f"pursuit-{index}"


def _pursuer_vanguard(index: int) -> MissionUnitConfig:
    return MissionUnitConfig(
        name=f"追撃格闘機 #{index}",
        max_hp=90,
        armor=6,
        mobility=1.9,
        weapon=MissionWeaponConfig(
            id=f"pursuer_saber_{index}",
            name="ヒートサーベル",
            power=30,
            range=60,
            accuracy=80,
            weapon_type="MELEE",
            is_melee=True,
            fire_arc_deg=360,
        ),
        role=UNIT_ROLE_VANGUARD,
        squad_id=_pursuit_squad(index),
    )


def _pursuer_sniper(index: int) -> MissionUnitConfig:
    return MissionUnitConfig(
        name=f"追撃狙撃機 #{index}",
        max_hp=70,
        armor=4,
        mobility=1.0,
        weapon=MissionWeaponConfig(
            id=f"pursuer_rifle_{index}",
            name="ロングライフル",
            power=28,
            range=600,
            accuracy=75,
        ),
        role=UNIT_ROLE_SNIPER,
        squad_id=_pursuit_squad(index),
    )


def build_retreat_support_mission() -> Mission:
    """撤退支援の作戦マスターを組み立てる（DB には入れない）."""
    allies = [
        _ally(1, 35, ["LEFT_ARM"]),
        _ally(2, 50, []),
        _ally(3, 30, ["RIGHT_LEG"]),
    ]
    enemies = [
        _pursuer_vanguard(1),
        _pursuer_vanguard(2),
        _pursuer_sniper(1),
        _pursuer_sniper(2),
    ]
    layout = MissionLayout(
        spawn_zones=[
            SpawnZone(
                team_id=MISSION_TEAM_PLAYER,
                center=Vector3(x=-250, y=0, z=0),
                radius=150,
            ),
            SpawnZone(
                team_id=MISSION_TEAM_ENEMY,
                center=Vector3(x=300, y=0, z=0),
                radius=150,
            ),
        ],
        retreat_points=[
            RetreatPoint(
                position=Vector3(x=-900, y=0, z=0),
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
        enemy_config={"enemies": [e.model_dump(mode="json") for e in enemies]},
        objective={
            "type": MISSION_OBJECTIVE_RETREAT_SUPPORT,
            "params": {"required": RETREAT_SUPPORT_REQUIRED},
        },
        allies_config=[a.model_dump(mode="json") for a in allies],
        layout=layout.model_dump(mode="json"),
        is_active=True,
    )
