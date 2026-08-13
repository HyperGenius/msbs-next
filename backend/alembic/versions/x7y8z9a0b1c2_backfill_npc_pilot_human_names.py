"""backfill_npc_pilot_human_names.

Revision ID: x7y8z9a0b1c2
Revises: w6x7y8z9a0b1
Create Date: 2026-08-13

Note:
    通常NPC（非エース）の pilots.name が機体名（例: "Zaku II (NPC)"）のまま
    保存されており没入感を損ねていた問題の一括修正 (Issue #444)。
    原因は matching_service.py の _create_npc_mobile_suit() が
    MobileSuit.pilot_name を設定しておらず、pilot_name = npc_suit.pilot_name
    or npc_suit.name のフォールバックで機体名がパイロット名に流用されていた
    ため（今回のコード修正で新規NPCは app.core.npc_data.generate_npc_pilot_name()
    による人名を使うよう修正済み）。本マイグレーションは既存データの一括バックフィル。

    エース由来のNPC（pilot_service.ACE_PILOT_NAMES）はすでに人名になっているため
    対象外とする。ダウングレードでは元の機体名を復元できないため no-op とする。
"""

import random
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "x7y8z9a0b1c2"
down_revision: str | Sequence[str] | None = "w6x7y8z9a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# npc_data.NPC_PILOT_FIRST_NAMES / NPC_PILOT_LAST_NAMES と同一の値を複製している。
# マイグレーションはアプリコードから独立させ、将来アプリ側の名簿が変わっても
# 過去のマイグレーションの再現性を壊さないようにするため。
NPC_PILOT_FIRST_NAMES = [
    "Jin",
    "Marco",
    "Elena",
    "Kaito",
    "Fenn",
    "Sara",
    "Dmitri",
    "Youko",
    "Leon",
    "Nadia",
    "Ryo",
    "Ingrid",
    "Theo",
    "Mika",
    "Otto",
    "Renna",
    "Hugo",
    "Saya",
    "Viktor",
    "Aina",
]

NPC_PILOT_LAST_NAMES = [
    "Reyes",
    "Voss",
    "Kagura",
    "Halden",
    "Iskandar",
    "Brandt",
    "Sumeragi",
    "Falk",
    "Orlov",
    "Tessin",
    "Nakada",
    "Wexler",
    "Ardin",
    "Kessler",
    "Blanc",
    "Mizushima",
    "Karlsen",
    "Torres",
    "Fenrir",
    "Amagi",
]

# npc_data.ACE_PILOTS の pilot_name 一覧を複製（エースは対象外にするため）。
ACE_PILOT_NAMES = frozenset(
    [
        "Char Aznable",
        "Ramba Ral",
        "Yazan Gable",
        "Amuro Ray",
        "Haman Karn",
    ]
)


def upgrade() -> None:
    """機体名になっている通常NPCのpilots.nameをランダムな人名で置き換える."""
    bind = op.get_bind()
    pilots = sa.table(
        "pilots",
        sa.column("id", sa.Uuid),
        sa.column("name", sa.String),
        sa.column("is_npc", sa.Boolean),
    )
    rows = bind.execute(
        sa.select(pilots.c.id, pilots.c.name).where(pilots.c.is_npc.is_(True))
    ).fetchall()

    for row in rows:
        if row.name in ACE_PILOT_NAMES:
            continue
        new_name = (
            f"{random.choice(NPC_PILOT_FIRST_NAMES)} "
            f"{random.choice(NPC_PILOT_LAST_NAMES)}"
        )
        bind.execute(pilots.update().where(pilots.c.id == row.id).values(name=new_name))


def downgrade() -> None:
    """データバックフィルのため元の機体名は復元できず no-op."""
    pass
