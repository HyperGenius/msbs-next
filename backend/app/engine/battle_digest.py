# backend/app/engine/battle_digest.py
"""バトル結果からダイジェスト（タグ・一言ログ）を生成する.

Battle History 一覧を「勝敗と日時の羅列」ではなく戦闘のダイジェストとして
表示するため、バトル終了時に一度だけ `sim.logs` を集計してタグを判定し、
タグごとのテンプレートプールから一言ログを生成する。完全ルールベースであり、
LLM等の外部呼び出しは行わない。
"""

import random
from dataclasses import dataclass

from app.models.models import BattleLog, MobileSuit

# --- タグ判定の閾値（初期見積もり。実プレイの分布を見て調整する前提） ---
SHINSHOU_HP_THRESHOLD = 20  # 辛勝: 最低到達HP%がこの値未満
ZENMETSU_KILLS_THRESHOLD = 5  # 殲滅: 撃破数がこの値以上
ISSEKI_DAMAGE_RATIO_THRESHOLD = 0.4  # 一撃必殺: 一撃が対象最大HPのこの比率以上
CHOUKISEN_STEP_RATIO_THRESHOLD = (
    0.7  # 長期戦: 消費ステップ数/最大ステップ数がこの値以上
)
KAIHI_MIN_ATTACKS = 3  # 回避特化: 判定に必要な最低被攻撃回数
KAIHI_DODGE_RATIO_THRESHOLD = 0.5  # 回避特化: 回避回数/被攻撃回数がこの値以上


@dataclass
class DigestStats:
    """戦闘ダイジェスト用の集計値（プレイヤー視点）."""

    win_loss: str
    kills: int
    player_survived: bool
    min_hp_percent: int
    damage_severity: str
    damage_taken_count: int
    max_hit_damage: int
    max_hit_ratio: float
    dodge_count: int
    attacks_received_count: int
    pilot_ms_name: str
    signature_weapon_name: str | None
    step_ratio: float


def _damage_severity(player_survived: bool, min_hp_percent: int) -> str:
    """最終HP割合から被弾ランク（表示用ラベル）を算出する."""
    if not player_survived:
        return "撃墜"
    if min_hp_percent >= 100:
        return "無傷"
    if min_hp_percent >= 70:
        return "軽微"
    if min_hp_percent >= 30:
        return "中破"
    return "大破"


def compute_digest_stats(
    player: MobileSuit,
    logs: list[BattleLog],
    kills: int,
    win_loss: str,
    steps_used: int,
    max_steps: int,
) -> DigestStats:
    """プレイヤー視点でバトルログを集計する.

    HPは回復要素がないため（simulation.py/combat.py に repair 処理なし）、
    最終 current_hp がそのままバトル中の最低到達HPと一致する前提で計算する。
    """
    player_survived = player.current_hp > 0
    min_hp_percent = (
        round(max(player.current_hp, 0) / player.max_hp * 100) if player.max_hp else 0
    )

    damage_taken_count = 0
    dodge_count = 0
    max_hit_ratio = 0.0
    max_hit_damage = 0
    weapon_counter: dict[str, int] = {}

    for log in logs:
        if log.target_id == player.id and log.action_type in ("ATTACK", "MELEE_COMBO"):
            damage_taken_count += 1
        elif log.target_id == player.id and log.action_type == "MISS":
            dodge_count += 1

        if log.actor_id == player.id and log.action_type == "ATTACK":
            if log.weapon_name:
                weapon_counter[log.weapon_name] = (
                    weapon_counter.get(log.weapon_name, 0) + 1
                )
            if log.damage and log.target_max_hp:
                ratio = log.damage / log.target_max_hp
                if ratio > max_hit_ratio:
                    max_hit_ratio = ratio
                    max_hit_damage = log.damage

    attacks_received_count = damage_taken_count + dodge_count
    signature_weapon_name = (
        max(weapon_counter, key=lambda name: weapon_counter[name])
        if weapon_counter
        else None
    )
    step_ratio = steps_used / max_steps if max_steps else 0.0

    return DigestStats(
        win_loss=win_loss,
        kills=kills,
        player_survived=player_survived,
        min_hp_percent=min_hp_percent,
        damage_severity=_damage_severity(player_survived, min_hp_percent),
        damage_taken_count=damage_taken_count,
        max_hit_damage=max_hit_damage,
        max_hit_ratio=max_hit_ratio,
        dodge_count=dodge_count,
        attacks_received_count=attacks_received_count,
        pilot_ms_name=player.name,
        signature_weapon_name=signature_weapon_name,
        step_ratio=step_ratio,
    )


def determine_tag(stats: DigestStats) -> str:
    """優先度リストに従いダイジェストタグを1つ判定する.

    WIN時: 辛勝 > 完封 > 殲滅 > 一撃必殺 > 長期戦 > 回避特化 > 通常
    LOSE/DRAWは別カテゴリとして扱う。
    """
    if stats.win_loss == "DRAW":
        return "痛み分け"
    if stats.win_loss == "LOSE":
        return "力戦及ばず" if stats.kills >= 1 else "完敗"

    if stats.min_hp_percent < SHINSHOU_HP_THRESHOLD:
        return "辛勝"
    if stats.damage_taken_count == 0:
        return "完封"
    if stats.kills >= ZENMETSU_KILLS_THRESHOLD:
        return "殲滅"
    if stats.max_hit_ratio >= ISSEKI_DAMAGE_RATIO_THRESHOLD:
        return "一撃必殺"
    if stats.step_ratio >= CHOUKISEN_STEP_RATIO_THRESHOLD:
        return "長期戦"
    if (
        stats.attacks_received_count >= KAIHI_MIN_ATTACKS
        and stats.dodge_count / stats.attacks_received_count
        >= KAIHI_DODGE_RATIO_THRESHOLD
    ):
        return "回避特化"
    return "通常"


TEMPLATE_POOLS: dict[str, list[str]] = {
    "辛勝": [
        "残り{min_hp}%まで削られながらも、{ms_name}が土壇場で持ち堪えた",
        "何度も撃墜の危機に瀕したが、{ms_name}は執念で生還を果たした",
        "被弾を重ねHP{min_hp}%というギリギリの状態での辛勝だった",
        "紙一重の攻防を制し、{ms_name}が命懸けの勝利をもぎ取った",
    ],
    "完封": [
        "効果的な{weapon_name}の運用により、敵の反撃を一切許さなかった",
        "終始戦況を支配し、被弾ゼロのまま完封勝利を収めた",
        "{ms_name}は隙のない立ち回りで、敵の攻撃を寄せ付けなかった",
        "完璧な立ち回りで、敵に一発も当てさせない完勝だった",
    ],
    "殲滅": [
        "{kills}機を沈め、戦場を制圧した",
        "{ms_name}の猛攻の前に、敵部隊は次々と撃墜されていった",
        "圧倒的な火力で{kills}機を屠り、戦場に{ms_name}の名を轟かせた",
        "敵編隊を一方的に殲滅し、完全勝利で戦闘を終えた",
    ],
    "一撃必殺": [
        "{weapon_name}の一撃が敵の急所を捉え、{max_hit_damage}ダメージの大戦果を挙げた",
        "渾身の一撃が敵機を一瞬で沈黙させた",
        "{ms_name}が放った{weapon_name}が、戦況を決定づける一撃となった",
        "一撃{max_hit_damage}ダメージ、敵の想定を超える火力で勝負を決めた",
    ],
    "長期戦": [
        "一進一退の攻防が続いたが、{ms_name}が粘り勝ちを収めた",
        "長期戦の末、{ms_name}が最後まで戦い抜いて勝利をつかんだ",
        "決め手を欠く消耗戦を制し、最終的に{ms_name}が勝ちを拾った",
        "長引く戦闘の中で敵の隙を見出し、じわじわと押し切った",
    ],
    "回避特化": [
        "敵ビームライフルの弾幕を掻い潜り、{ms_name}が接近戦に持ち込んだ",
        "巧みな機動で攻撃をかいくぐり、被弾を最小限に抑えての勝利だった",
        "{ms_name}の卓越した回避機動が、この勝利の決め手となった",
        "紙一重の回避を繰り返しながら、着実に敵を仕留めた",
    ],
    "通常": [
        "{ms_name}が着実に敵を撃破し、勝利を収めた",
        "堅実な立ち回りで、{ms_name}が戦闘を制した",
        "大きな波乱もなく、{ms_name}が勝利を収めた",
    ],
    "力戦及ばず": [
        "{kills}機を道連れにしたが、力及ばず{ms_name}は撃墜された",
        "奮戦むなしく、{ms_name}は数の不利を覆せなかった",
        "互角の戦いを繰り広げたが、最後は敵の攻勢に屈した",
    ],
    "完敗": [
        "反撃の糸口を掴めぬまま、{ms_name}は撃墜された",
        "敵の圧倒的な攻勢の前に、なすすべなく敗北した",
        "距離を詰められず、一方的な展開のまま戦闘を終えた",
    ],
    "痛み分け": [
        "決着はつかず、両者痛み分けに終わった",
        "激しい応酬の末、勝敗を決めることなく戦闘は終了した",
        "決定打を欠いたまま、時間切れで戦闘が終わった",
    ],
}


def _render_template(template: str, stats: DigestStats) -> str:
    """テンプレート文字列にダイジェスト集計値を埋め込む."""
    return template.format(
        ms_name=stats.pilot_ms_name,
        min_hp=stats.min_hp_percent,
        kills=stats.kills,
        weapon_name=stats.signature_weapon_name or "武装",
        max_hit_damage=stats.max_hit_damage,
    )


def build_digest(stats: DigestStats, avoid_text: str | None = None) -> tuple[str, str]:
    """タグを判定し、テンプレートプールから一言ログを生成する.

    Args:
        stats: compute_digest_stats() で算出した集計値
        avoid_text: 直前のバトルで使用済みの一言ログ（連続選出を避けるため）

    Returns:
        (digest_tag, digest_text) のタプル
    """
    tag = determine_tag(stats)
    candidates = [_render_template(t, stats) for t in TEMPLATE_POOLS[tag]]
    if avoid_text is not None and len(candidates) > 1:
        filtered = [c for c in candidates if c != avoid_text]
        if filtered:
            candidates = filtered
    return tag, random.choice(candidates)
