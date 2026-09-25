#!/usr/bin/env python3
"""Verification script for NPC personality and ace pilot features.

エースパイロットは ace_pilots テーブルから読み込むため、
インメモリDBに data/master/ace_pilots.json をシードしてから検証する。
"""

import json
import os
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# Set a dummy database URL to avoid import errors
os.environ.setdefault("NEON_DATABASE_URL", "postgresql://dummy:dummy@dummy/dummy")

from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.db as app_db
from app.core.gamedata import get_ace_pilots
from app.core.npc_data import BATTLE_CHATTER, PERSONALITY_TYPES
from app.models.models import AcePilot
from app.services.matching_service import MatchingService

_ACE_PILOTS_JSON = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "master"
    / "ace_pilots.json"
)


def json_serializer(*args, **kwargs):
    """Simple JSON serializer for in-memory database."""
    return json.dumps(*args, **kwargs)


def _setup_in_memory_db():
    """インメモリDBを作成し、gamedata の参照先に差し替えてエースをシードする."""
    engine = create_engine(
        "sqlite://",
        json_serializer=json_serializer,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    app_db.engine = engine

    with Session(engine) as session:
        for item in json.loads(_ACE_PILOTS_JSON.read_text(encoding="utf-8")):
            session.add(AcePilot(**item))
        session.commit()
    return engine


def test_ace_pilot_data():
    """Verify ace pilot data is correctly defined."""
    print("=" * 60)
    print("Ace Pilot Data Verification")
    print("=" * 60)

    aces = get_ace_pilots()
    print(f"\n総エースパイロット数: {len(aces)}")

    for ace in aces:
        print(f"\n【{ace['name']}】")
        print(f"  パイロット名: {ace['pilot_name']}")
        print(f"  性格: {ace['personality']}")
        print(f"  機体: {ace['mobile_suit']['name']}")
        print(f"  HP: {ace['mobile_suit']['max_hp']}")
        print(f"  機動性: {ace['mobile_suit']['mobility']}")
        print(f"  武器数: {len(ace['mobile_suit']['weapons'])}")
        print(f"  賞金経験値: {ace['bounty_exp']}")
        print(f"  賞金クレジット: {ace['bounty_credits']}")


def test_personality_system():
    """Verify personality system is correctly defined."""
    print("\n" + "=" * 60)
    print("Personality System Verification")
    print("=" * 60)

    print(f"\n性格タイプ数: {len(PERSONALITY_TYPES)}")
    print(f"性格タイプ: {', '.join(PERSONALITY_TYPES)}")

    for personality in PERSONALITY_TYPES:
        print(f"\n【{personality}】")
        if personality in BATTLE_CHATTER:
            chatter = BATTLE_CHATTER[personality]
            print(f"  攻撃時セリフ数: {len(chatter.get('attack', []))}")
            print(f"  被弾時セリフ数: {len(chatter.get('hit', []))}")
            print(f"  撃墜時セリフ数: {len(chatter.get('destroyed', []))}")
            print(f"  ミス時セリフ数: {len(chatter.get('miss', []))}")

            # サンプルセリフを表示
            if chatter.get("attack"):
                print(f"  攻撃時セリフ例: 「{chatter['attack'][0]}」")
            if chatter.get("hit"):
                print(f"  被弾時セリフ例: 「{chatter['hit'][0]}」")


def test_npc_creation(engine):
    """Test NPC creation with personality."""
    print("\n" + "=" * 60)
    print("NPC Creation Test")
    print("=" * 60)

    with Session(engine) as session:
        service = MatchingService(session)

        # Create several NPCs
        print("\n通常NPC生成テスト:")
        for i in range(5):
            npc = service._create_npc_mobile_suit()
            print(f"\nNPC {i + 1}:")
            print(f"  名前: {npc.name}")
            print(f"  性格: {npc.personality}")
            print(f"  戦術: {npc.tactics}")
            print(f"  HP: {npc.max_hp}")
            print(f"  機動性: {npc.mobility:.2f}")

        # Create ace pilots
        print("\n\nエースパイロット生成テスト:")
        for i in range(3):
            ace = service._create_ace_pilot()
            if ace is None:
                raise RuntimeError("ace_pilots テーブルが空です")
            print(f"\nエース {i + 1}:")
            print(f"  名前: {ace.name}")
            print(f"  パイロット名: {ace.pilot_name}")
            print(f"  性格: {ace.personality}")
            print(f"  戦術: {ace.tactics}")
            print(f"  HP: {ace.max_hp}")
            print(f"  機動性: {ace.mobility:.2f}")
            print(f"  賞金経験値: {ace.bounty_exp}")
            print(f"  賞金クレジット: {ace.bounty_credits}")
            print(f"  エースフラグ: {ace.is_ace}")


def test_battle_chatter_examples():
    """Show some example battle chatter."""
    print("\n" + "=" * 60)
    print("Battle Chatter Examples")
    print("=" * 60)

    for personality in PERSONALITY_TYPES:
        print(f"\n【{personality}】")
        if personality in BATTLE_CHATTER:
            chatter = BATTLE_CHATTER[personality]

            print("  攻撃時:")
            for i in range(min(3, len(chatter["attack"]))):
                print(f"    - 「{chatter['attack'][i]}」")

            print("  被弾時:")
            for i in range(min(3, len(chatter["hit"]))):
                print(f"    - 「{chatter['hit'][i]}」")

            print("  撃墜時:")
            for i in range(min(2, len(chatter["destroyed"]))):
                print(f"    - 「{chatter['destroyed'][i]}」")


def main():
    """Run all verification tests."""
    try:
        engine = _setup_in_memory_db()
        test_ace_pilot_data()
        test_personality_system()
        test_npc_creation(engine)
        test_battle_chatter_examples()

        print("\n" + "=" * 60)
        print("✓ All verification tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
