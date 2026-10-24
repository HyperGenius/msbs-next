"""add_trainer_to_master_mobile_suits.

Revision ID: r3f4a5b6c7d8
Revises: q2e3f4a5b6c7
Create Date: 2026-10-24

Note:
    練習機（初期支給機体）を機体マスターで管理する。
    これまで `app/core/gamedata.py` の `STARTER_KITS` にハードコードしていた値を投入する。
    同じIDの機体マスターが既にあれば投入しない。

    練習機は設計図マスターを作らない。ショップ・設計図のドロップ・設計図コレクションの対象外にするため。
    武器スロット数は 2 にする。機体マスターに無かったころ、所持機体は `MAX_WEAPON_SLOTS`（2）で解決していたため。

    所持機体の `master_mobile_suit_id` のバックフィルは
    `scripts/maintenance/backfill_trainer_master_id.py` で行う。
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r3f4a5b6c7d8"
down_revision: str | Sequence[str] | None = "q2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _trainer_specs(weapon: dict) -> dict:
    return {
        "max_hp": 700,
        "armor": 40,
        "mobility": 1.0,
        "sensor_range": 500.0,
        "beam_resistance": 0.0,
        "physical_resistance": 0.0,
        "max_en": 200,
        "en_recovery": 10,
        "melee_aptitude": 1.0,
        "shooting_aptitude": 1.0,
        "accuracy_bonus": 0.0,
        "evasion_bonus": 0.0,
        "acceleration_bonus": 1.0,
        "turning_bonus": 1.0,
        "weapons": [
            {
                **weapon,
                "power": 80,
                "range": 400,
                "accuracy": 60,
                "optimal_range": 300.0,
                "decay_rate": 0.08,
                "is_melee": False,
            }
        ],
        "missing_parts": [],
        "terrain_adaptability": {},
    }


_TRAINERS = [
    {
        "id": "gm_trainer",
        "name": "RGM-79T GM Trainer",
        "model_number": "RGM-79T",
        "faction": "FEDERATION",
        "starter_faction": "FEDERATION",
        "description": "地球連邦軍の練習用モビルスーツ。全勢力共通の標準スペック。",
        "specs": _trainer_specs(
            {
                "id": "trainer_spray_gun",
                "name": "Beam Spray Gun(Trainer)",
                "type": "BEAM",
            }
        ),
    },
    {
        "id": "zaku_ii_trainer",
        "name": "MS-06T Zaku II Trainer",
        "model_number": "MS-06T",
        "faction": "ZEON",
        "starter_faction": "ZEON",
        "description": "ジオン公国軍の練習用モビルスーツ。全勢力共通の標準スペック。",
        "specs": _trainer_specs(
            {
                "id": "trainer_machine_gun",
                "name": "Zaku Machine Gun(Trainer)",
                "type": "PHYSICAL",
            }
        ),
    },
]


def upgrade() -> None:
    """Add is_trainer / starter_faction to master_mobile_suits and insert trainers."""
    op.add_column(
        "master_mobile_suits",
        sa.Column(
            "is_trainer", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "master_mobile_suits",
        sa.Column("starter_faction", sa.String(), nullable=True),
    )

    conn = op.get_bind()
    existing = {
        row[0] for row in conn.execute(sa.text("SELECT id FROM master_mobile_suits"))
    }
    table = sa.table(
        "master_mobile_suits",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("name_ja", sa.String),
        sa.column("model_number", sa.String),
        sa.column("price", sa.Integer),
        sa.column("faction", sa.String),
        sa.column("description", sa.String),
        sa.column("weapon_slot_count", sa.Integer),
        sa.column("beam_generator_lv", sa.Integer),
        sa.column("is_trainer", sa.Boolean),
        sa.column("starter_faction", sa.String),
        sa.column("specs", sa.JSON),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.now(UTC)
    rows = [
        {
            **trainer,
            "name_ja": "",
            "price": 0,
            "weapon_slot_count": 2,
            "beam_generator_lv": 0,
            "is_trainer": True,
            "created_at": now,
            "updated_at": now,
        }
        for trainer in _TRAINERS
        if trainer["id"] not in existing
    ]
    if rows:
        op.bulk_insert(table, rows)


def downgrade() -> None:
    """Delete trainers and drop is_trainer / starter_faction."""
    op.execute("DELETE FROM master_mobile_suits WHERE is_trainer")
    op.drop_column("master_mobile_suits", "starter_faction")
    op.drop_column("master_mobile_suits", "is_trainer")
