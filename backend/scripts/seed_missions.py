# backend/scripts/seed_missions.py
import os
import sys

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session

from app.db import engine
from app.models.models import Mission

# ミッションデータ
missions = [
    Mission(
        id=1,
        name="Mission 01: ザク小隊",
        difficulty=1,
        description="3機のザクII小隊を撃破せよ",
        enemy_config={
            "enemies": [
                {
                    "name": "ザクII #1",
                    "max_hp": 80,
                    "armor": 5,
                    "mobility": 1.2,
                    "position": {"x": 500, "y": -200, "z": 0},
                    "weapon": {
                        "id": "zaku_mg_1",
                        "name": "ザクマシンガン",
                        "power": 15,
                        "range": 400,
                        "accuracy": 70,
                    },
                },
                {
                    "name": "ザクII #2",
                    "max_hp": 80,
                    "armor": 5,
                    "mobility": 1.2,
                    "position": {"x": 500, "y": 0, "z": 0},
                    "weapon": {
                        "id": "zaku_mg_2",
                        "name": "ザクマシンガン",
                        "power": 15,
                        "range": 400,
                        "accuracy": 70,
                    },
                },
                {
                    "name": "ザクII #3",
                    "max_hp": 80,
                    "armor": 5,
                    "mobility": 1.2,
                    "position": {"x": 500, "y": 200, "z": 0},
                    "weapon": {
                        "id": "zaku_mg_3",
                        "name": "ザクマシンガン",
                        "power": 15,
                        "range": 400,
                        "accuracy": 70,
                    },
                },
            ]
        },
    ),
    Mission(
        id=2,
        name="Mission 02: 防衛線突破",
        difficulty=2,
        description="4機のザクII防衛部隊を突破せよ",
        enemy_config={
            "enemies": [
                {
                    "name": "ザクII #1",
                    "max_hp": 100,
                    "armor": 8,
                    "mobility": 1.3,
                    "position": {"x": 400, "y": -300, "z": 0},
                    "weapon": {
                        "id": "zaku_mg_1",
                        "name": "ザクマシンガン",
                        "power": 18,
                        "range": 400,
                        "accuracy": 75,
                    },
                },
                {
                    "name": "ザクII #2",
                    "max_hp": 100,
                    "armor": 8,
                    "mobility": 1.3,
                    "position": {"x": 400, "y": -100, "z": 0},
                    "weapon": {
                        "id": "zaku_mg_2",
                        "name": "ザクマシンガン",
                        "power": 18,
                        "range": 400,
                        "accuracy": 75,
                    },
                },
                {
                    "name": "ザクII #3",
                    "max_hp": 100,
                    "armor": 8,
                    "mobility": 1.3,
                    "position": {"x": 400, "y": 100, "z": 0},
                    "weapon": {
                        "id": "zaku_mg_3",
                        "name": "ザクマシンガン",
                        "power": 18,
                        "range": 400,
                        "accuracy": 75,
                    },
                },
                {
                    "name": "ザクII #4",
                    "max_hp": 100,
                    "armor": 8,
                    "mobility": 1.3,
                    "position": {"x": 400, "y": 300, "z": 0},
                    "weapon": {
                        "id": "zaku_mg_4",
                        "name": "ザクマシンガン",
                        "power": 18,
                        "range": 400,
                        "accuracy": 75,
                    },
                },
            ]
        },
    ),
    Mission(
        id=3,
        name="Mission 03: エース部隊撃破",
        difficulty=3,
        description="高性能ザクII 2機を撃破せよ",
        enemy_config={
            "enemies": [
                {
                    "name": "ザクII S型 #1",
                    "max_hp": 120,
                    "armor": 12,
                    "mobility": 1.5,
                    "position": {"x": 450, "y": -150, "z": 0},
                    "weapon": {
                        "id": "zaku_mg_s1",
                        "name": "ザクマシンガン改",
                        "power": 22,
                        "range": 450,
                        "accuracy": 80,
                    },
                },
                {
                    "name": "ザクII S型 #2",
                    "max_hp": 120,
                    "armor": 12,
                    "mobility": 1.5,
                    "position": {"x": 450, "y": 150, "z": 0},
                    "weapon": {
                        "id": "zaku_mg_s2",
                        "name": "ザクマシンガン改",
                        "power": 22,
                        "range": 450,
                        "accuracy": 80,
                    },
                },
            ]
        },
    ),
]

with Session(engine) as session:
    for mission in missions:
        # Check if mission already exists
        existing = session.get(Mission, mission.id)
        if existing:
            print(f"Mission {mission.id} already exists, skipping...")
            continue
        session.add(mission)
        print(f"Added: {mission.name}")
    session.commit()
    print("Mission seed complete!")

exit()
