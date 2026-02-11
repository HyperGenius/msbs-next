#!/usr/bin/env python3
"""Verification script for NPC personality and ace pilot features."""

import os
import sys
import json

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Set a dummy database URL to avoid import errors
os.environ.setdefault("NEON_DATABASE_URL", "postgresql://dummy:dummy@dummy/dummy")

from sqlmodel import Session, create_engine, SQLModel
from app.services.matching_service import MatchingService
from app.core.npc_data import ACE_PILOTS, PERSONALITY_TYPES, BATTLE_CHATTER


def json_serializer(*args, **kwargs):
    """Simple JSON serializer for in-memory database."""
    return json.dumps(*args, **kwargs)


def test_ace_pilot_data():
    """Verify ace pilot data is correctly defined."""
    print("=" * 60)
    print("Ace Pilot Data Verification")
    print("=" * 60)
    
    print(f"\n総エースパイロット数: {len(ACE_PILOTS)}")
    
    for ace in ACE_PILOTS:
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
            if chatter.get('attack'):
                print(f"  攻撃時セリフ例: 「{chatter['attack'][0]}」")
            if chatter.get('hit'):
                print(f"  被弾時セリフ例: 「{chatter['hit'][0]}」")


def test_npc_creation():
    """Test NPC creation with personality."""
    print("\n" + "=" * 60)
    print("NPC Creation Test")
    print("=" * 60)
    
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:", json_serializer=json_serializer)
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        service = MatchingService(session)
        
        # Create several NPCs
        print("\n通常NPC生成テスト:")
        for i in range(5):
            npc = service._create_npc_mobile_suit()
            print(f"\nNPC {i+1}:")
            print(f"  名前: {npc.name}")
            print(f"  性格: {npc.personality}")
            print(f"  戦術: {npc.tactics}")
            print(f"  HP: {npc.max_hp}")
            print(f"  機動性: {npc.mobility:.2f}")
            
        # Create ace pilots
        print("\n\nエースパイロット生成テスト:")
        for i in range(3):
            ace = service._create_ace_pilot()
            print(f"\nエース {i+1}:")
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
    
    import random
    
    for personality in PERSONALITY_TYPES:
        print(f"\n【{personality}】")
        if personality in BATTLE_CHATTER:
            chatter = BATTLE_CHATTER[personality]
            
            print("  攻撃時:")
            for i in range(min(3, len(chatter['attack']))):
                print(f"    - 「{chatter['attack'][i]}」")
            
            print("  被弾時:")
            for i in range(min(3, len(chatter['hit']))):
                print(f"    - 「{chatter['hit'][i]}」")
            
            print("  撃墜時:")
            for i in range(min(2, len(chatter['destroyed']))):
                print(f"    - 「{chatter['destroyed'][i]}」")


def main():
    """Run all verification tests."""
    try:
        test_ace_pilot_data()
        test_personality_system()
        test_npc_creation()
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
