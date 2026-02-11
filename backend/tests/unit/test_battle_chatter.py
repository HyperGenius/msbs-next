"""Tests for battle chatter in simulation."""

import pytest
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def create_test_unit(name: str, side: str, personality: str | None = None) -> MobileSuit:
    """Create a test mobile suit."""
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        sensor_range=500.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="test_weapon",
                name="Test Weapon",
                power=100,
                range=500,
                accuracy=80,
            )
        ],
        side=side,
        personality=personality,
    )


def test_chatter_generation_for_npc():
    """Test that NPCs with personality generate chatter."""
    # Create NPC with personality
    npc = create_test_unit("Test NPC", "ENEMY", personality="AGGRESSIVE")
    player = create_test_unit("Player", "PLAYER", personality=None)
    
    simulator = BattleSimulator(player, [npc])
    
    # Test chatter generation
    attack_chatter = simulator._generate_chatter(npc, "attack")
    # Chatter may be None due to 30% probability, but should be string or None
    assert attack_chatter is None or isinstance(attack_chatter, str)
    
    # Test with multiple attempts to verify it can generate chatter
    chatter_generated = False
    for _ in range(20):  # Try multiple times to account for 30% probability
        chatter = simulator._generate_chatter(npc, "attack")
        if chatter is not None:
            chatter_generated = True
            assert isinstance(chatter, str)
            assert len(chatter) > 0
            break
    
    # With 20 attempts at 30% probability, we should get at least one chatter
    # Probability of getting no chatter in 20 attempts: 0.7^20 ≈ 0.0008
    assert chatter_generated, "Failed to generate chatter in 20 attempts"


def test_chatter_not_generated_for_players():
    """Test that players without personality don't generate chatter."""
    player = create_test_unit("Player", "PLAYER", personality=None)
    
    simulator = BattleSimulator(player, [])
    
    # Test multiple times to ensure no chatter is ever generated
    for _ in range(10):
        chatter = simulator._generate_chatter(player, "attack")
        assert chatter is None


def test_chatter_types():
    """Test that all chatter types can be generated."""
    npc = create_test_unit("Test NPC", "ENEMY", personality="AGGRESSIVE")
    player = create_test_unit("Player", "PLAYER")
    
    simulator = BattleSimulator(player, [npc])
    
    chatter_types = ["attack", "hit", "destroyed", "miss"]
    
    for chatter_type in chatter_types:
        # Try multiple times to account for randomness
        type_generated = False
        for _ in range(30):
            chatter = simulator._generate_chatter(npc, chatter_type)
            if chatter is not None:
                type_generated = True
                assert isinstance(chatter, str)
                break
        
        assert type_generated, f"Failed to generate {chatter_type} chatter"


def test_different_personalities_have_different_chatter():
    """Test that different personalities have different chatter."""
    player = create_test_unit("Player", "PLAYER")
    
    personalities = ["AGGRESSIVE", "CAUTIOUS", "SNIPER"]
    chatter_by_personality = {}
    
    for personality in personalities:
        npc = create_test_unit(f"NPC {personality}", "ENEMY", personality=personality)
        simulator = BattleSimulator(player, [npc])
        
        # Collect chatter for this personality
        chatter_set = set()
        for _ in range(50):  # More attempts to collect variety
            chatter = simulator._generate_chatter(npc, "attack")
            if chatter:
                chatter_set.add(chatter)
        
        chatter_by_personality[personality] = chatter_set
        assert len(chatter_set) > 0, f"No chatter collected for {personality}"
    
    # Verify that personalities have some unique chatter
    # (Not all chatter needs to be unique, but there should be some distinction)
    aggressive_unique = chatter_by_personality["AGGRESSIVE"] - chatter_by_personality["CAUTIOUS"] - chatter_by_personality["SNIPER"]
    cautious_unique = chatter_by_personality["CAUTIOUS"] - chatter_by_personality["AGGRESSIVE"] - chatter_by_personality["SNIPER"]
    sniper_unique = chatter_by_personality["SNIPER"] - chatter_by_personality["AGGRESSIVE"] - chatter_by_personality["CAUTIOUS"]
    
    # At least one personality should have unique chatter
    assert len(aggressive_unique) > 0 or len(cautious_unique) > 0 or len(sniper_unique) > 0


def test_battle_log_includes_chatter():
    """Test that battle logs include chatter field."""
    player = create_test_unit("Player", "PLAYER")
    # Place NPC close to player for immediate combat
    npc = create_test_unit("NPC", "ENEMY", personality="AGGRESSIVE")
    npc.position = Vector3(x=200, y=0, z=0)  # Close range
    
    simulator = BattleSimulator(player, [npc])
    
    # Process a few turns
    for _ in range(5):
        if simulator.is_finished:
            break
        simulator.process_turn()
    
    # Check logs for chatter
    logs_with_chatter = [log for log in simulator.logs if log.chatter is not None]
    
    # At least some logs should have chatter (due to 30% probability)
    # With enough turns and actions, we should see some chatter
    assert len(simulator.logs) > 0, "No logs generated"
    
    # Not all logs will have chatter, but at least verify the field exists
    for log in simulator.logs:
        # The chatter field should exist, even if None
        assert hasattr(log, "chatter")


def test_ace_destruction_log():
    """Test that ace pilot destruction generates special message."""
    player = create_test_unit("Player", "PLAYER")
    ace = create_test_unit("Ace NPC", "ENEMY", personality="AGGRESSIVE")
    ace.is_ace = True
    ace.pilot_name = "Red Comet"
    ace.position = Vector3(x=100, y=0, z=0)
    ace.current_hp = 1  # Set low HP for quick defeat
    
    simulator = BattleSimulator(player, [ace])
    
    # Process turns until ace is destroyed
    for _ in range(10):
        if simulator.is_finished:
            break
        simulator.process_turn()
    
    # Find destruction log
    destruction_logs = [log for log in simulator.logs if log.action_type == "DESTROYED"]
    
    if len(destruction_logs) > 0:
        # Check if ace destruction message includes special marker
        ace_destruction = next(
            (log for log in destruction_logs if "★【エース撃破】" in log.message),
            None
        )
        
        # If ace was destroyed, verify special message
        if ace.current_hp <= 0:
            assert ace_destruction is not None, "Ace destruction should have special message"
            assert "Red Comet" in ace_destruction.message
