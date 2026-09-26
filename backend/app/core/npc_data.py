"""NPC data definitions.

エースパイロットのマスターデータは ace_pilots テーブルで管理する。
参照は app.core.gamedata.get_ace_pilots() / get_ace_pilot_by_id() を使うこと。
"""

import random

# --- Personality Types ---

PERSONALITY_TYPES = ["AGGRESSIVE", "CAUTIOUS", "SNIPER"]


def build_npc_tactics(personality: str) -> dict[str, str]:
    """性格に応じた NPC の戦術設定を生成する.

    Returns:
        priority と range を持つ戦術設定。未知の性格は SNIPER として扱う。
    """
    if personality == "AGGRESSIVE":
        return {"priority": random.choice(["CLOSEST", "WEAKEST"]), "range": "MELEE"}
    if personality == "CAUTIOUS":
        return {"priority": random.choice(["WEAKEST", "RANDOM"]), "range": "BALANCED"}
    return {"priority": "CLOSEST", "range": "RANGED"}


# --- NPC Pilot Name Generation ---
# 通常NPC（非エース）のパイロット名。機体名をそのままパイロット名に流用していた
# 問題（Issue #444）の修正用。組み合わせでランダムなパイロット名を生成する。

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


def generate_npc_pilot_name() -> str:
    """通常NPC用のランダムなパイロット名(名 姓)を生成する."""
    first = random.choice(NPC_PILOT_FIRST_NAMES)
    last = random.choice(NPC_PILOT_LAST_NAMES)
    return f"{first} {last}"


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
