"""戦闘計算モジュール.

バランス調整用の純粋関数として実装された計算ロジック。
パイロットステータス（DEX/INT/REF/TOU/LUK）が戦闘各種計算に与える影響を管理する。

Note:
    全ての関数はステータスがゼロ（デフォルト）の場合、従来と同一の計算結果を返す。
"""

import random
from dataclasses import dataclass, field


@dataclass
class PilotStats:
    """パイロットステータス.

    Attributes:
        sht: 射撃精度 (SHT) - 射撃攻撃力補正率（シグモイド入力）
        mel: 格闘技巧 (MEL) - 格闘攻撃力補正率（シグモイド入力）
        intel: 直感 (INT) - クリティカル率・回避率
        ref: 反応 (REF) - イニシアチブ・機動性乗算
        tou: 耐久 (TOU) - 攻撃ダメージ加算・被クリティカル率低下・防御加算
        luk: 幸運 (LUK) - ダメージ乱数偏り・完全回避
    """

    sht: int = field(default=0)
    mel: int = field(default=0)
    intel: int = field(default=0)
    ref: int = field(default=0)
    tou: int = field(default=0)
    luk: int = field(default=0)


def calculate_hit_chance(
    base_hit_chance: float,
    distance_from_optimal: float = 0.0,
    decay_rate: float = 0.05,
    attacker_dex: int = 0,
    defender_int: int = 0,
) -> float:
    """命中率を計算する（パイロットステータス補正適用）.

    DEX（攻撃側）: 基礎命中率の上昇（+0.5%/DEX）、距離減衰ペナルティの緩和
    INT（防御側）: 基礎回避率への固定値加算（-0.3%/INT）

    Args:
        base_hit_chance: スキルや機体パラメータを適用した後の基礎命中率
        distance_from_optimal: 最適射程からの距離差（DEX による緩和計算に使用）
        decay_rate: 武器の距離減衰係数
        attacker_dex: 攻撃側の DEX ステータス値
        defender_int: 防御側の INT ステータス値

    Returns:
        float: 調整後の命中率（0〜100 にクランプ済み）
    """
    hit = base_hit_chance

    if attacker_dex > 0:
        # DEX: 基礎命中率の上昇
        hit += attacker_dex * 0.5
        # DEX: 距離減衰ペナルティの緩和（最大50%まで回復）
        distance_penalty = distance_from_optimal * decay_rate
        reduction = min(attacker_dex * 0.01, 0.5)
        hit += distance_penalty * reduction

    if defender_int > 0:
        # INT: 基礎回避率への加算（命中率を低下させる）
        hit -= defender_int * 0.3

    return max(0.0, min(100.0, hit))


def calculate_critical_chance(
    base_crit_rate: float,
    attacker_int: int = 0,
    defender_tou: int = 0,
) -> float:
    """クリティカル率を計算する（パイロットステータス補正適用）.

    INT（攻撃側）: クリティカル率の大幅上昇（+1%/INT）
    TOU（防御側）: 被クリティカル率の低下（-0.5%/TOU）

    Args:
        base_crit_rate: スキルを適用した後の基礎クリティカル率（0.0〜1.0）
        attacker_int: 攻撃側の INT ステータス値
        defender_tou: 防御側の TOU ステータス値

    Returns:
        float: 調整後のクリティカル率（0.0〜1.0 にクランプ済み）
    """
    crit = base_crit_rate

    if attacker_int > 0:
        # INT: クリティカル率の上昇
        crit += attacker_int * 0.01

    if defender_tou > 0:
        # TOU: 被クリティカル率の低下
        crit -= defender_tou * 0.005

    return max(0.0, min(1.0, crit))


def calculate_damage_variance(
    base_damage: int,
    attacker_luk: int = 0,
    attacker_tou: int = 0,
    defender_dex: int = 0,
    defender_tou: int = 0,
    defender_luk: int = 0,
) -> tuple[int, bool]:
    """ダメージの乱数変動とステータス補正を計算する.

    TOU（攻撃側）: 基礎ダメージへの固定値加算（+1/TOU）
    TOU（防御側）: 装甲への固定値加算（ダメージから -1/TOU を差し引き）
    DEX（防御側）: 最終被ダメージの割合カット（0.5%/DEX、最大15%）
    LUK（攻撃側）: ダメージ計算時の乱数を最大値方向へ偏らせる
    LUK（防御側）: 極低確率での完全回避（0.1%/LUK、最大5%）

    Note:
        全ステータスがゼロの場合、従来と同じ ``random.uniform(0.9, 1.1)`` の乱数変動になる。

    Args:
        base_damage: 機体パラメータ・スキル・武器耐性を適用した後のダメージ値
        attacker_luk: 攻撃側の LUK ステータス値
        attacker_tou: 攻撃側の TOU ステータス値
        defender_dex: 防御側の DEX ステータス値
        defender_tou: 防御側の TOU ステータス値
        defender_luk: 防御側の LUK ステータス値

    Returns:
        tuple[int, bool]: (最終ダメージ, 完全回避フラグ)
            完全回避フラグが True の場合、ダメージは 0 で奇跡的な回避が発生している。
    """
    # LUK（防御側）: 完全回避チェック
    if defender_luk > 0:
        perfect_evade_chance = min(defender_luk * 0.001, 0.05)  # 最大5%
        if random.random() < perfect_evade_chance:
            return 0, True  # 完全回避

    damage = base_damage

    # TOU（攻撃側）: 基礎ダメージへの固定値加算
    damage += attacker_tou

    # 乱数変動（LUK による最大値への偏り）
    if attacker_luk > 0:
        # LUKが高いほど乱数が最大値に偏る（べき乗による分布の偏り）
        luk_factor = max(0.1, 1.0 - attacker_luk * 0.05)
        r = random.random()
        variance = 0.9 + 0.2 * (r**luk_factor)
    else:
        # ステータスゼロの場合は従来どおりの一様乱数
        variance = random.uniform(0.9, 1.1)

    damage = int(damage * variance)

    # TOU（防御側）: 装甲への固定値加算（ダメージ軽減）
    damage = max(0, damage - defender_tou)

    # DEX（防御側）: 最終ダメージの割合カット
    if defender_dex > 0:
        dex_cut = min(defender_dex * 0.005, 0.15)  # 最大15%カット
        damage = int(damage * (1.0 - dex_cut))

    return damage, False


def calculate_initiative(
    mobility: float,
    ref_stat: int = 0,
) -> float:
    """イニシアチブ（行動順決定値）を計算する.

    REF: ターン内の行動順決定値ボーナス、機動性に対する乗算ボーナス（+2%/REF）

    Note:
        REF がゼロの場合、戻り値は `mobility` と同一になる（従来と互換）。

    Args:
        mobility: 機体の基礎機動性
        ref_stat: パイロットの REF ステータス値

    Returns:
        float: 行動順決定値（値が高いほど先に行動する）
    """
    ref_multiplier = 1.0 + ref_stat * 0.02
    return mobility * ref_multiplier
