"""add_blueprint_tables.

Revision ID: i3d4e5f6a7b8
Revises: h2c3d4e5f6a7
Create Date: 2026-09-26

Note:
    設計図マスター (master_blueprints) と所持設計図 (player_blueprints) を追加する。
    既存の機体・武器マスターには、標準配備の設計図マスターを作成する。
    導入直後にショップの挙動を変えないため、全件を標準配備にする。
    既存プレイヤーの所持機体・所持武器には、対応する設計図を MIGRATION で付与する。

    ショップ購入機は master_mobile_suit_id が NULL なので、機体名で機体マスターを引く。
    改名した機体と練習機はマスターを引けないため、付与の対象外になる。
    NPC の機体・武器 (user_id が NULL、または pilots.is_npc の所有) も対象外にする。
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "h2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# blueprint_service の値を複製している。
# アプリ側の値が変わっても、このマイグレーションの結果を変えないため。
MOBILE_SUIT = "MOBILE_SUIT"
WEAPON = "WEAPON"
MIGRATION_SOURCE = "MIGRATION"
DUPLICATE_CREDIT_RATIO = 0.2

master_blueprints = sa.table(
    "master_blueprints",
    sa.column("id", sa.String()),
    sa.column("target_type", sa.String()),
    sa.column("target_id", sa.String()),
    sa.column("is_standard_issue", sa.Boolean()),
    sa.column("duplicate_credit_value", sa.Integer()),
    sa.column("created_at", sa.DateTime()),
    sa.column("updated_at", sa.DateTime()),
)

player_blueprints = sa.table(
    "player_blueprints",
    sa.column("id", sa.Uuid()),
    sa.column("user_id", sa.String()),
    sa.column("blueprint_id", sa.String()),
    sa.column("source", sa.String()),
    sa.column("source_battle_id", sa.Uuid()),
    sa.column("acquired_at", sa.DateTime()),
)


def _blueprint_id(target_type: str, target_id: str) -> str:
    return f"{target_type.lower()}:{target_id}"


def _create_tables() -> None:
    op.create_table(
        "master_blueprints",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("is_standard_issue", sa.Boolean(), nullable=False),
        sa.Column("duplicate_credit_value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "target_type", "target_id", name="uq_master_blueprint_target"
        ),
    )
    op.create_index(
        "ix_master_blueprints_target_id", "master_blueprints", ["target_id"]
    )

    op.create_table(
        "player_blueprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("blueprint_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_battle_id", sa.Uuid(), nullable=True),
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["blueprint_id"], ["master_blueprints.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "blueprint_id", name="uq_player_blueprint"),
    )
    op.create_index("ix_player_blueprints_user_id", "player_blueprints", ["user_id"])
    op.create_index(
        "ix_player_blueprints_blueprint_id", "player_blueprints", ["blueprint_id"]
    )


def _seed_master_blueprints(conn: sa.Connection, now: datetime) -> None:
    rows = []
    for target_type, table in (
        (MOBILE_SUIT, "master_mobile_suits"),
        (WEAPON, "master_weapons"),
    ):
        for target_id, price in conn.execute(sa.text(f"SELECT id, price FROM {table}")):
            rows.append(
                {
                    "id": _blueprint_id(target_type, target_id),
                    "target_type": target_type,
                    "target_id": target_id,
                    "is_standard_issue": True,
                    "duplicate_credit_value": int(price * DUPLICATE_CREDIT_RATIO),
                    "created_at": now,
                    "updated_at": now,
                }
            )
    if rows:
        op.bulk_insert(master_blueprints, rows)


def _owned_mobile_suit_targets(conn: sa.Connection) -> set[tuple[str, str]]:
    master_id_by_name: dict[str, str] = {
        name: ms_id
        for ms_id, name in conn.execute(
            sa.text("SELECT id, name FROM master_mobile_suits")
        )
    }
    master_ids = set(master_id_by_name.values())
    owned = conn.execute(
        sa.text(
            "SELECT user_id, name, master_mobile_suit_id FROM mobile_suits "
            "WHERE user_id IS NOT NULL "
            "AND user_id NOT IN (SELECT user_id FROM pilots WHERE is_npc)"
        )
    )
    targets: set[tuple[str, str]] = set()
    for user_id, name, master_mobile_suit_id in owned:
        master_id = master_mobile_suit_id or master_id_by_name.get(name)
        if master_id in master_ids:
            targets.add((user_id, _blueprint_id(MOBILE_SUIT, master_id)))
    return targets


def _owned_weapon_targets(conn: sa.Connection) -> set[tuple[str, str]]:
    owned = conn.execute(
        sa.text(
            "SELECT DISTINCT user_id, master_weapon_id FROM player_weapons "
            "WHERE master_weapon_id IN (SELECT id FROM master_weapons) "
            "AND user_id NOT IN (SELECT user_id FROM pilots WHERE is_npc)"
        )
    )
    return {
        (user_id, _blueprint_id(WEAPON, master_weapon_id))
        for user_id, master_weapon_id in owned
    }


def _grant_owned_blueprints(conn: sa.Connection, now: datetime) -> None:
    targets = _owned_mobile_suit_targets(conn) | _owned_weapon_targets(conn)
    rows = [
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "blueprint_id": blueprint_id,
            "source": MIGRATION_SOURCE,
            "source_battle_id": None,
            "acquired_at": now,
        }
        for user_id, blueprint_id in sorted(targets)
    ]
    if rows:
        op.bulk_insert(player_blueprints, rows)


def upgrade() -> None:
    """Create blueprint tables and grant blueprints for owned items."""
    _create_tables()
    conn = op.get_bind()
    now = datetime.now(UTC)
    _seed_master_blueprints(conn, now)
    _grant_owned_blueprints(conn, now)


def downgrade() -> None:
    """Drop blueprint tables."""
    op.drop_index("ix_player_blueprints_blueprint_id", table_name="player_blueprints")
    op.drop_index("ix_player_blueprints_user_id", table_name="player_blueprints")
    op.drop_table("player_blueprints")
    op.drop_index("ix_master_blueprints_target_id", table_name="master_blueprints")
    op.drop_table("master_blueprints")
