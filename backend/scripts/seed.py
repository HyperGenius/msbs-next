# backend/scripts/seed.py
import os
import sys

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session

from app.db import engine
from app.models.models import BattleResult, Mission, MobileSuit, Weapon

# 武器データ
rifle = Weapon(
    id="w1",
    name="Beam Rifle",
    power=300,
    range=600,
    accuracy=80,
    type="BEAM",
    optimal_range=400.0,
    decay_rate=0.05,
)
mg = Weapon(
    id="w2",
    name="Zaku MG",
    power=100,
    range=400,
    accuracy=60,
    type="PHYSICAL",
    optimal_range=300.0,
    decay_rate=0.08,
)

# 機体データ
gundam = MobileSuit(
    name="Gundam",
    max_hp=1000,
    armor=100,
    mobility=1.5,
    weapons=[rifle],
    beam_resistance=0.2,
    physical_resistance=0.1,
)
zaku = MobileSuit(
    name="Zaku II",
    max_hp=800,
    armor=50,
    mobility=1.0,
    weapons=[mg],
    beam_resistance=0.05,
    physical_resistance=0.2,
)

with Session(engine) as session:
    # モビルスーツを追加
    session.add(gundam)
    session.add(zaku)

    # ミッションを追加（簡易テンプレート参照形式）
    mission = Mission(
        id=1,
        name="Tutorial",
        difficulty=1,
        description="Basic introduction mission.",
        enemy_config={
            "enemies": [
                {
                    # ここでは作成した Zaku の ID を参照する簡易的な形式を使用
                    "mobile_suit_id": str(zaku.id),
                    "count": 1,
                }
            ]
        },
    )
    session.add(mission)
    # Ensure mission is flushed to DB so foreign key constraint succeeds
    session.flush()

    # サンプルのバトル結果（デバッグ用）
    sample_logs = [
        {
            "turn": 0,
            "actor_id": str(gundam.id),
            "action_type": "ATTACK",
            "target_id": str(zaku.id),
            "damage": 120,
            "message": "Gundam fires Beam Rifle",
            "position_snapshot": {"x": 0.0, "y": 0.0, "z": 0.0},
        }
    ]

    battle_result = BattleResult(
        user_id=None,
        mission_id=mission.id,
        win_loss="WIN",
        logs=sample_logs,
    )
    session.add(battle_result)

    session.commit()

exit()
