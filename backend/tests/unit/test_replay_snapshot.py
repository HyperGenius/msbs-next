"""Test BattleResult replay snapshot fields."""

import uuid

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import json_serializer
from app.models.models import BattleResult, MobileSuit, Vector3, Weapon


@pytest.fixture(name="session")
def session_fixture():
    """テスト用のインメモリDBセッションを作成."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        json_serializer=json_serializer,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_battle_result_has_replay_fields():
    """BattleResultモデルにリプレイ用フィールドがあることを確認."""
    assert hasattr(BattleResult, "environment")
    assert hasattr(BattleResult, "player_info")
    assert hasattr(BattleResult, "enemies_info")


def test_battle_result_with_snapshot(session: Session):
    """スナップショット付きBattleResultの保存・取得を確認."""
    player = MobileSuit(
        name="Test Gundam",
        max_hp=1000,
        current_hp=1000,
        armor=100,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="beam_rifle", name="Beam Rifle",
                power=300, range=600, accuracy=85,
            )
        ],
        side="PLAYER",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )

    enemy = MobileSuit(
        name="Test Zaku",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        position=Vector3(x=500, y=0, z=0),
        weapons=[
            Weapon(
                id="zaku_mg", name="Zaku Machine Gun",
                power=100, range=400, accuracy=70,
            )
        ],
        side="ENEMY",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )

    result = BattleResult(
        user_id="test_user",
        win_loss="WIN",
        logs=[],
        environment="GROUND",
        player_info=player.model_dump(),
        enemies_info=[enemy.model_dump()],
    )

    session.add(result)
    session.commit()
    session.refresh(result)

    assert result.environment == "GROUND"
    assert result.player_info is not None
    assert result.player_info["name"] == "Test Gundam"
    assert result.enemies_info is not None
    assert len(result.enemies_info) == 1
    assert result.enemies_info[0]["name"] == "Test Zaku"


def test_battle_result_without_snapshot(session: Session):
    """スナップショット無しの古いデータとの互換性を確認."""
    result = BattleResult(
        user_id="test_user",
        win_loss="LOSE",
        logs=[],
    )

    session.add(result)
    session.commit()
    session.refresh(result)

    assert result.environment == "SPACE"
    assert result.player_info is None
    assert result.enemies_info is None


def test_battle_result_default_environment():
    """environmentのデフォルト値がSPACEであることを確認."""
    result = BattleResult(win_loss="DRAW", logs=[])
    assert result.environment == "SPACE"
