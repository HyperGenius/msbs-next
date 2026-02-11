"""NPC and Ace Pilot data definitions."""

from app.models.models import Weapon

# --- Personality Types ---

PERSONALITY_TYPES = ["AGGRESSIVE", "CAUTIOUS", "SNIPER"]

# --- Battle Chatter (Personality-based dialogue) ---

BATTLE_CHATTER = {
    "AGGRESSIVE": {
        "attack": [
            "落ちろォォ！",
            "当たれ！",
            "逃がすか！",
            "そこだ！",
            "食らえ！",
            "いけぇ！",
        ],
        "hit": [
            "しまっ…！",
            "くっ…！",
            "痛いじゃないか！",
            "この程度か！",
            "まだまだ！",
        ],
        "destroyed": [
            "まだ…やれる…",
            "バカな…！",
            "こんなところで…",
            "認めん…認めんぞ…！",
        ],
        "miss": [
            "ちっ、外したか！",
            "しまった！",
            "くそっ！",
        ],
    },
    "CAUTIOUS": {
        "attack": [
            "狙い撃つ！",
            "慎重に…",
            "これで決める！",
            "確実に仕留める！",
        ],
        "hit": [
            "まずい…！",
            "退くべきか…",
            "危険だ…",
            "距離を取らねば！",
        ],
        "destroyed": [
            "やはり…無理だったか…",
            "これまでか…",
            "判断を誤った…",
        ],
        "miss": [
            "慎重に行こう…",
            "焦るな…",
            "次だ…",
        ],
    },
    "SNIPER": {
        "attack": [
            "狙撃する！",
            "捉えた…",
            "射程内だ！",
            "照準良し！",
        ],
        "hit": [
            "接近されたか！",
            "距離を取る！",
            "近すぎる！",
        ],
        "destroyed": [
            "射程が…足りなかった…",
            "接近を許すとは…",
        ],
        "miss": [
            "風を読み違えた…",
            "再照準…",
            "距離を測り直す…",
        ],
    },
}

# --- Ace Pilot Master Data ---

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
            "mobility": 3.0,  # 通常の3倍！
            "sensor_range": 700.0,
            "beam_resistance": 0.1,
            "physical_resistance": 0.25,
            "max_en": 1500,
            "en_recovery": 150,
            "weapons": [
                Weapon(
                    id="ace_zaku_mg",
                    name="High Mobility Zaku Machine Gun",
                    power=150,
                    range=500,
                    accuracy=85,
                    type="PHYSICAL",
                    optimal_range=350.0,
                    decay_rate=0.05,
                ),
                Weapon(
                    id="ace_heat_hawk",
                    name="Heat Hawk",
                    power=200,
                    range=150,
                    accuracy=90,
                    type="PHYSICAL",
                    optimal_range=100.0,
                    decay_rate=0.1,
                ),
            ],
            "tactics": {"priority": "WEAKEST", "range": "MELEE"},
        },
        "bounty_exp": 500,
        "bounty_credits": 1000,
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
                Weapon(
                    id="ace_heat_rod",
                    name="Heat Rod",
                    power=180,
                    range=350,
                    accuracy=88,
                    type="PHYSICAL",
                    optimal_range=250.0,
                    decay_rate=0.08,
                ),
                Weapon(
                    id="ace_gatling_shield",
                    name="Gatling Shield",
                    power=140,
                    range=300,
                    accuracy=80,
                    type="PHYSICAL",
                    optimal_range=200.0,
                    decay_rate=0.1,
                ),
            ],
            "tactics": {"priority": "CLOSEST", "range": "MELEE"},
        },
        "bounty_exp": 450,
        "bounty_credits": 900,
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
                Weapon(
                    id="ace_sea_serpent",
                    name="Sea Serpent",
                    power=170,
                    range=400,
                    accuracy=82,
                    type="BEAM",
                    optimal_range=300.0,
                    decay_rate=0.07,
                    en_cost=80,
                ),
                Weapon(
                    id="ace_fedayeen_rifle",
                    name="Fedayeen Rifle",
                    power=160,
                    range=450,
                    accuracy=78,
                    type="PHYSICAL",
                    optimal_range=350.0,
                    decay_rate=0.08,
                ),
            ],
            "tactics": {"priority": "RANDOM", "range": "BALANCED"},
        },
        "bounty_exp": 480,
        "bounty_credits": 950,
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
                Weapon(
                    id="ace_beam_rifle",
                    name="Beam Rifle",
                    power=350,
                    range=700,
                    accuracy=92,
                    type="BEAM",
                    optimal_range=450.0,
                    decay_rate=0.04,
                    en_cost=100,
                ),
                Weapon(
                    id="ace_beam_saber",
                    name="Beam Saber",
                    power=250,
                    range=180,
                    accuracy=95,
                    type="BEAM",
                    optimal_range=120.0,
                    decay_rate=0.1,
                    en_cost=60,
                ),
            ],
            "tactics": {"priority": "THREAT", "range": "BALANCED"},
        },
        "bounty_exp": 800,
        "bounty_credits": 2000,
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
                Weapon(
                    id="ace_funnel",
                    name="Funnel",
                    power=280,
                    range=800,
                    accuracy=88,
                    type="BEAM",
                    optimal_range=600.0,
                    decay_rate=0.03,
                    en_cost=120,
                ),
                Weapon(
                    id="ace_beam_saber_qubeley",
                    name="Beam Saber",
                    power=220,
                    range=170,
                    accuracy=90,
                    type="BEAM",
                    optimal_range=110.0,
                    decay_rate=0.12,
                    en_cost=50,
                ),
            ],
            "tactics": {"priority": "STRONGEST", "range": "RANGED"},
        },
        "bounty_exp": 750,
        "bounty_credits": 1800,
    },
]


def get_ace_pilot_by_id(ace_id: str) -> dict | None:
    """Get ace pilot data by ID.

    Args:
        ace_id: Ace pilot ID

    Returns:
        dict | None: Ace pilot data. None if not found
    """
    for ace in ACE_PILOTS:
        if ace["id"] == ace_id:
            return ace
    return None
