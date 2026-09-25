"""add_ace_pilots_table.

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-09-25

Note:
    npc_data.py にハードコードされていたエースパイロットの静的マスターデータ
    (ACE_PILOTS) を ace_pilots テーブルへ移行する。
    master_mobile_suits / master_weapons と同じ「スネークケースID文字列PK +
    スペックはJSON列」のパターンを踏襲する。

    投入データは移行時点の ACE_PILOTS を複製している。マイグレーションはアプリコード
    から独立させ、将来アプリ側の定義が変わっても過去のマイグレーションの再現性を
    壊さないようにするため。weapons は Weapon のデフォルト値と異なる項目のみを保持し、
    読み出し時に Weapon(**w) で既定値を補完する（移行前の挙動と同一）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9f0a1b2c3d4"
down_revision: str | Sequence[str] | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACE_PILOTS = [
    {
        "id": "ace_char_aznable",
        "name": "赤い彗星",
        "pilot_name": "Char Aznable",
        "description": "通常の3倍の速度を持つエースパイロット",
        "personality": "AGGRESSIVE",
        "mobile_suit": {
            "name": "High Mobility Zaku II (Red)",
            "max_hp": 1200,
            "armor": 80,
            "mobility": 3.0,
            "sensor_range": 700.0,
            "beam_resistance": 0.1,
            "physical_resistance": 0.25,
            "max_en": 1500,
            "en_recovery": 150,
            "weapons": [
                {
                    "id": "ace_zaku_mg",
                    "name": "High Mobility Zaku Machine Gun",
                    "power": 150,
                    "range": 500.0,
                    "accuracy": 85.0,
                    "type": "PHYSICAL",
                    "optimal_range": 350.0,
                    "decay_rate": 0.05,
                },
                {
                    "id": "ace_heat_hawk",
                    "name": "Heat Hawk",
                    "power": 200,
                    "range": 150.0,
                    "accuracy": 90.0,
                    "type": "PHYSICAL",
                    "optimal_range": 100.0,
                    "decay_rate": 0.1,
                },
            ],
            "tactics": {"priority": "WEAKEST", "range": "MELEE"},
        },
        "bounty_exp": 500,
        "bounty_credits": 1000,
        "stats": {"sht": 10, "mel": 10, "intel": 9, "ref": 15, "tou": 7, "luk": 8},
        "skills": {"flanking": 3},
    },
    {
        "id": "ace_ramba_ral",
        "name": "青き巨星",
        "pilot_name": "Ramba Ral",
        "description": "ベテランパイロット。近接戦闘のスペシャリスト",
        "personality": "AGGRESSIVE",
        "mobile_suit": {
            "name": "Gouf Custom (Blue)",
            "max_hp": 1300,
            "armor": 90,
            "mobility": 2.0,
            "sensor_range": 650.0,
            "beam_resistance": 0.12,
            "physical_resistance": 0.2,
            "max_en": 1400,
            "en_recovery": 140,
            "weapons": [
                {
                    "id": "ace_heat_rod",
                    "name": "Heat Rod",
                    "power": 180,
                    "range": 350.0,
                    "accuracy": 88.0,
                    "type": "PHYSICAL",
                    "optimal_range": 250.0,
                    "decay_rate": 0.08,
                },
                {
                    "id": "ace_gatling_shield",
                    "name": "Gatling Shield",
                    "power": 140,
                    "range": 300.0,
                    "accuracy": 80.0,
                    "type": "PHYSICAL",
                    "optimal_range": 200.0,
                    "decay_rate": 0.1,
                },
            ],
            "tactics": {"priority": "CLOSEST", "range": "MELEE"},
        },
        "bounty_exp": 450,
        "bounty_credits": 900,
        "stats": {"sht": 7, "mel": 14, "intel": 8, "ref": 10, "tou": 12, "luk": 6},
        "skills": {"flanking": 3},
    },
    {
        "id": "ace_yazan_gable",
        "name": "紫豚",
        "pilot_name": "Yazan Gable",
        "description": "残虐な戦闘狂。高い攻撃性を持つ",
        "personality": "AGGRESSIVE",
        "mobile_suit": {
            "name": "Hambrabi (Purple)",
            "max_hp": 1100,
            "armor": 70,
            "mobility": 2.5,
            "sensor_range": 680.0,
            "beam_resistance": 0.15,
            "physical_resistance": 0.15,
            "max_en": 1600,
            "en_recovery": 160,
            "weapons": [
                {
                    "id": "ace_sea_serpent",
                    "name": "Sea Serpent",
                    "power": 170,
                    "range": 400.0,
                    "accuracy": 82.0,
                    "type": "BEAM",
                    "optimal_range": 300.0,
                    "decay_rate": 0.07,
                    "en_cost": 80,
                },
                {
                    "id": "ace_fedayeen_rifle",
                    "name": "Fedayeen Rifle",
                    "power": 160,
                    "range": 450.0,
                    "accuracy": 78.0,
                    "type": "PHYSICAL",
                    "optimal_range": 350.0,
                    "decay_rate": 0.08,
                },
            ],
            "tactics": {"priority": "RANDOM", "range": "BALANCED"},
        },
        "bounty_exp": 480,
        "bounty_credits": 950,
        "stats": {"sht": 10, "mel": 13, "intel": 7, "ref": 11, "tou": 13, "luk": 5},
        "skills": {"flanking": 3},
    },
    {
        "id": "ace_amuro_ray",
        "name": "白い悪魔",
        "pilot_name": "Amuro Ray",
        "description": "ニュータイプパイロット。圧倒的な性能",
        "personality": "CAUTIOUS",
        "mobile_suit": {
            "name": "RX-78-2 Gundam",
            "max_hp": 1500,
            "armor": 120,
            "mobility": 2.2,
            "sensor_range": 800.0,
            "beam_resistance": 0.25,
            "physical_resistance": 0.15,
            "max_en": 2000,
            "en_recovery": 200,
            "weapons": [
                {
                    "id": "ace_beam_rifle",
                    "name": "Beam Rifle",
                    "power": 350,
                    "range": 700.0,
                    "accuracy": 92.0,
                    "type": "BEAM",
                    "optimal_range": 450.0,
                    "decay_rate": 0.04,
                    "en_cost": 100,
                },
                {
                    "id": "ace_beam_saber",
                    "name": "Beam Saber",
                    "power": 250,
                    "range": 180.0,
                    "accuracy": 95.0,
                    "type": "BEAM",
                    "optimal_range": 120.0,
                    "decay_rate": 0.1,
                    "en_cost": 60,
                },
            ],
            "tactics": {"priority": "THREAT", "range": "BALANCED"},
        },
        "bounty_exp": 800,
        "bounty_credits": 2000,
        "stats": {"sht": 13, "mel": 11, "intel": 15, "ref": 14, "tou": 9, "luk": 12},
        "skills": {"flanking": 2},
    },
    {
        "id": "ace_haman_karn",
        "name": "ハマーンの影",
        "pilot_name": "Haman Karn",
        "description": "強化人間。高い精神感応能力",
        "personality": "SNIPER",
        "mobile_suit": {
            "name": "Qubeley",
            "max_hp": 1400,
            "armor": 100,
            "mobility": 2.3,
            "sensor_range": 900.0,
            "beam_resistance": 0.3,
            "physical_resistance": 0.1,
            "max_en": 2200,
            "en_recovery": 220,
            "weapons": [
                {
                    "id": "ace_funnel",
                    "name": "Funnel",
                    "power": 280,
                    "range": 800.0,
                    "accuracy": 88.0,
                    "type": "BEAM",
                    "optimal_range": 600.0,
                    "decay_rate": 0.03,
                    "en_cost": 120,
                },
                {
                    "id": "ace_beam_saber_qubeley",
                    "name": "Beam Saber",
                    "power": 220,
                    "range": 170.0,
                    "accuracy": 90.0,
                    "type": "BEAM",
                    "optimal_range": 110.0,
                    "decay_rate": 0.12,
                    "en_cost": 50,
                },
            ],
            "tactics": {"priority": "STRONGEST", "range": "RANGED"},
        },
        "bounty_exp": 750,
        "bounty_credits": 1800,
        "stats": {"sht": 11, "mel": 10, "intel": 14, "ref": 11, "tou": 8, "luk": 13},
        "skills": {"flanking": 2},
    },
]


def upgrade() -> None:
    """Create ace_pilots table and seed the existing ace pilots."""
    op.create_table(
        "ace_pilots",
        sa.Column(
            "id",
            sa.String(),
            nullable=False,
            comment="スネークケースID (例: ace_char_aznable)",
        ),
        sa.Column("name", sa.String(), nullable=False, comment="二つ名"),
        sa.Column("pilot_name", sa.String(), nullable=False, comment="パイロット名"),
        sa.Column(
            "description",
            sa.String(),
            nullable=False,
            server_default="",
            comment="説明文",
        ),
        sa.Column(
            "personality",
            sa.String(),
            nullable=False,
            comment="性格タイプ (AGGRESSIVE/CAUTIOUS/SNIPER)",
        ),
        sa.Column(
            "mobile_suit",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="搭乗機体スペック (AcePilotMobileSuitSpec の全フィールド)",
        ),
        sa.Column(
            "bounty_exp",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="撃破時のボーナス経験値",
        ),
        sa.Column(
            "bounty_credits",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="撃破時のボーナスクレジット",
        ),
        sa.Column(
            "stats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="パイロットステータス (sht/mel/intel/ref/tou/luk)",
        ),
        sa.Column(
            "skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="スキルレベル (スキルID→レベル)",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    ace_pilots_table = sa.table(
        "ace_pilots",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("pilot_name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("personality", sa.String()),
        sa.column("mobile_suit", postgresql.JSONB()),
        sa.column("bounty_exp", sa.Integer()),
        sa.column("bounty_credits", sa.Integer()),
        sa.column("stats", postgresql.JSONB()),
        sa.column("skills", postgresql.JSONB()),
    )
    op.bulk_insert(ace_pilots_table, ACE_PILOTS)


def downgrade() -> None:
    """Drop ace_pilots table."""
    op.drop_table("ace_pilots")
