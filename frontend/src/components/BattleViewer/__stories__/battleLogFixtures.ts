/* frontend/src/components/BattleViewer/__stories__/battleLogFixtures.ts */

import { BattleLog, MobileSuit, Vector3, Weapon } from "@/types/battle";

// Storybook 専用のバトルログ生成ヘルパー。
// message の文言は backend/app/engine/combat.py の出力に合わせる。
// 演出判定が message の文字列に依存するため、文言がずれると本番で出ない演出を再現してしまう。

export const PLAYER_ID = "story-player";
export const ENEMY_ID = "story-enemy";

/** 自機の初期位置（フィールド中央付近）。 */
export const PLAYER_ORIGIN: Vector3 = { x: 2300, y: 0, z: 2500 };

export const WEAPONS = {
    BEAM_RIFLE: {
        id: "beam_rifle",
        name: "ビームライフル",
        power: 300,
        range: 600,
        accuracy: 70,
        type: "BEAM",
        weapon_type: "RANGED",
        en_cost: 50,
    },
    MACHINE_GUN: {
        id: "zaku_mg",
        name: "ザクマシンガン",
        power: 60,
        range: 400,
        accuracy: 60,
        type: "PHYSICAL",
        weapon_type: "RANGED",
        max_ammo: 30,
    },
    BEAM_SABER: {
        id: "beam_saber",
        name: "ビームサーベル",
        power: 250,
        range: 50,
        accuracy: 80,
        type: "BEAM",
        weapon_type: "MELEE",
        is_melee: true,
    },
    HEAT_HAWK: {
        id: "heat_hawk",
        name: "ヒートホーク",
        power: 200,
        range: 50,
        accuracy: 75,
        type: "PHYSICAL",
        weapon_type: "MELEE",
        is_melee: true,
    },
} satisfies Record<string, Weapon>;

export type WeaponKey = keyof typeof WEAPONS;

export function makeMobileSuit(overrides: Partial<MobileSuit> & Pick<MobileSuit, "id" | "name" | "side">): MobileSuit {
    return {
        max_hp: 1000,
        current_hp: 1000,
        armor: 20,
        mobility: 1.5,
        sensor_range: 800,
        position: { x: 0, y: 0, z: 0 },
        weapons: [WEAPONS.BEAM_RIFLE, WEAPONS.BEAM_SABER],
        tactics: { priority: "CLOSEST", range: "BALANCED" },
        max_en: 1000,
        ...overrides,
    };
}

function baseLog(timestamp: number, actor: MobileSuit, pos: Vector3): BattleLog {
    return {
        timestamp,
        actor_id: actor.id,
        action_type: "WAIT",
        message: "",
        position_snapshot: pos,
    };
}

/** backend の _get_damage_description と同じ閾値でダメージ表現を返す。 */
function damageDescription(damage: number, target: MobileSuit): string {
    const ratio = damage / Math.max(1, target.max_hp);
    if (ratio >= 0.2) return "致命的なヒット";
    if (ratio >= 0.1) return "手痛いダメージ";
    if (ratio >= 0.05) return "ダメージ";
    return "軽微なダメージ";
}

function attackLogBase(actor: MobileSuit, weapon: Weapon, hitChance: number): string {
    return `${actor.name}が[${weapon.name}]で攻撃！ (命中: ${hitChance}%)`;
}

export function moveLog(
    timestamp: number,
    actor: MobileSuit,
    pos: Vector3,
    velocity?: Vector3,
    heading?: number,
): BattleLog {
    return {
        ...baseLog(timestamp, actor, pos),
        action_type: "MOVE",
        message: `${actor.name}が移動中`,
        velocity_snapshot: velocity,
        heading,
    };
}

export function detectionLog(timestamp: number, actor: MobileSuit, target: MobileSuit, pos: Vector3): BattleLog {
    return {
        ...baseLog(timestamp, actor, pos),
        action_type: "DETECTION",
        target_id: target.id,
        message: `${actor.name}が中距離に${target.name}を発見！`,
    };
}

export function attackHitLog(params: {
    timestamp: number;
    actor: MobileSuit;
    target: MobileSuit;
    actorPos: Vector3;
    weapon: Weapon;
    damage: number;
    isCrit?: boolean;
    /** EN 武器の場合は消費後の EN 残量を { en } で渡す（Issue #533） */
    details?: Record<string, unknown>;
}): BattleLog {
    const { timestamp, actor, target, actorPos, weapon, damage, isCrit = false, details } = params;
    const desc = damageDescription(damage, target);
    const hitText = isCrit ? " -> ★★ クリティカルヒット！！" : " -> 命中！";
    const damageText = isCrit
        ? ` 弱点を的確に捉え、${target.name}に${damage}ダメージ！（${desc}）`
        : ` ${target.name}に${damage}ダメージ！（${desc}）`;
    return {
        ...baseLog(timestamp, actor, actorPos),
        action_type: "ATTACK",
        target_id: target.id,
        damage,
        target_max_hp: target.max_hp,
        message: `${attackLogBase(actor, weapon, 65)}${hitText}${damageText}`,
        weapon_name: weapon.name,
        weapon_id: weapon.id,
        is_crit: isCrit,
        details,
    };
}

export function missLog(params: {
    timestamp: number;
    actor: MobileSuit;
    target: MobileSuit;
    actorPos: Vector3;
    weapon: Weapon;
}): BattleLog {
    const { timestamp, actor, target, actorPos, weapon } = params;
    return {
        ...baseLog(timestamp, actor, actorPos),
        action_type: "MISS",
        target_id: target.id,
        message: `${attackLogBase(actor, weapon, 40)} -> ${target.name}に回避された！`,
        weapon_name: weapon.name,
        weapon_id: weapon.id,
    };
}

export function meleeComboLog(params: {
    timestamp: number;
    actor: MobileSuit;
    target: MobileSuit;
    actorPos: Vector3;
    weapon: Weapon;
    comboCount: number;
    totalDamage: number;
}): BattleLog {
    const { timestamp, actor, target, actorPos, weapon, comboCount, totalDamage } = params;
    const comboMessage = `${comboCount}Combo ${totalDamage}ダメージ!!`;
    return {
        ...baseLog(timestamp, actor, actorPos),
        action_type: "MELEE_COMBO",
        target_id: target.id,
        damage: totalDamage,
        target_max_hp: target.max_hp,
        message: `${actor.name} の格闘コンボ！ ${comboMessage}`,
        weapon_name: weapon.name,
        weapon_id: weapon.id,
        combo_count: comboCount,
        combo_message: comboMessage,
    };
}

// EN 関連ログの message / details は backend の action_handler.py / movement.py / combat.py に合わせる（Issue #533）
export function boostStartLog(timestamp: number, actor: MobileSuit, pos: Vector3, en: number): BattleLog {
    return {
        ...baseLog(timestamp, actor, pos),
        action_type: "BOOST_START",
        message: `${actor.name} がブーストダッシュを開始した！`,
        details: { en },
    };
}

export function boostEndLog(timestamp: number, actor: MobileSuit, pos: Vector3, en: number): BattleLog {
    const depleted = en <= 0;
    const reason = depleted ? "EN 枯渇" : "最大継続時間";
    return {
        ...baseLog(timestamp, actor, pos),
        action_type: "BOOST_END",
        message: `${actor.name} のブーストが終了した (理由: ${reason})`,
        details: depleted ? { reason, en, reason_code: "EN_DEPLETED" } : { reason, en },
    };
}

export function enShortageWaitLog(timestamp: number, actor: MobileSuit, pos: Vector3, weapon: Weapon): BattleLog {
    return {
        ...baseLog(timestamp, actor, pos),
        message: `${actor.name}はENが枯渇し、[${weapon.name}]を使えず待機中`,
        details: { reason_code: "EN_SHORTAGE" },
    };
}

export function destroyedLog(timestamp: number, unit: MobileSuit, pos: Vector3): BattleLog {
    return {
        ...baseLog(timestamp, unit, pos),
        action_type: "DESTROYED",
        message: `${unit.name} は爆散した...`,
    };
}

// backend/app/engine/constants.py の COMBO_DAMAGE_MULTIPLIER と揃える。
const COMBO_DAMAGE_MULTIPLIER = 1.5;

export type EffectKind = "HIT" | "CRITICAL" | "MISS" | "MELEE_COMBO" | "RAPID_FIRE";

/** RAPID_FIRE で同時刻に出す命中ログの数。数字が縦に積まれることを確認するため。 */
const RAPID_FIRE_HITS = 3;

export interface EffectScenarioOptions {
    effect: EffectKind;
    attacker: "PLAYER" | "ENEMY";
    weapon: WeaponKey;
    /** 自機と敵機の距離（m）。 */
    distance: number;
    damage: number;
    /** effect が MELEE_COMBO のときだけ使う。 */
    comboCount: number;
}

export interface EffectScenario {
    logs: BattleLog[];
    player: MobileSuit;
    enemies: MobileSuit[];
    /** 演出ログを置いたタイムスタンプ（秒）。 */
    eventTimestamp: number;
}

// 0 秒は演出なしの待機状態にする。
// 再生ラッパーが 0 秒と演出時刻を往復して演出を繰り返し発火させるため。
const EFFECT_EVENT_TIMESTAMP = 0.5;

/** 1 対 1 で演出を 1 回だけ発生させるログ一式を作る。 */
export function buildEffectScenario(options: EffectScenarioOptions): EffectScenario {
    const { effect, attacker, weapon: weaponKey, distance, damage, comboCount } = options;
    const weapon = WEAPONS[weaponKey];
    const playerPos = PLAYER_ORIGIN;
    const enemyPos = { x: PLAYER_ORIGIN.x + distance, y: 0, z: PLAYER_ORIGIN.z };

    const player = makeMobileSuit({
        id: PLAYER_ID,
        name: "ガンダム",
        side: "PLAYER",
        position: playerPos,
        weapons: [weapon],
    });
    const enemy = makeMobileSuit({
        id: ENEMY_ID,
        name: "ザクII (NPC)",
        side: "ENEMY",
        position: enemyPos,
        weapons: [weapon],
        is_npc: true,
    });

    const [actor, target, actorPos, targetPos] =
        attacker === "PLAYER"
            ? [player, enemy, playerPos, enemyPos]
            : [enemy, player, enemyPos, playerPos];

    const t = EFFECT_EVENT_TIMESTAMP;
    const logs: BattleLog[] = [
        // 敵機は自機の DETECTION ログが無いと描画されない
        detectionLog(0, player, enemy, playerPos),
        moveLog(0, player, playerPos),
        moveLog(0, enemy, enemyPos),
        moveLog(t, target, targetPos),
    ];

    switch (effect) {
        case "HIT":
            logs.push(attackHitLog({ timestamp: t, actor, target, actorPos, weapon, damage }));
            break;
        case "CRITICAL":
            logs.push(attackHitLog({ timestamp: t, actor, target, actorPos, weapon, damage, isCrit: true }));
            break;
        case "MISS":
            logs.push(missLog({ timestamp: t, actor, target, actorPos, weapon }));
            break;
        case "RAPID_FIRE":
            for (let i = 0; i < RAPID_FIRE_HITS; i++) {
                logs.push(attackHitLog({ timestamp: t, actor, target, actorPos, weapon, damage }));
            }
            break;
        case "MELEE_COMBO":
            // backend は格闘命中の ATTACK を出した直後に MELEE_COMBO を出す
            logs.push(attackHitLog({ timestamp: t, actor, target, actorPos, weapon, damage }));
            logs.push(
                meleeComboLog({
                    timestamp: t,
                    actor,
                    target,
                    actorPos,
                    weapon,
                    comboCount,
                    totalDamage: Math.floor(damage * COMBO_DAMAGE_MULTIPLIER) * comboCount,
                }),
            );
            break;
    }

    return { logs, player, enemies: [enemy], eventTimestamp: t };
}
