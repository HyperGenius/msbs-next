/* frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts */

import { BattleLog, MobileSuit } from "@/types/battle";
import { DEFAULT_MAX_EN, EN_WARNING_THRESHOLD } from "../utils";
import { WarningType } from "../types";

/** 浮動小数点数の誤差許容値（タイムスタンプ比較用） */
const TIMESTAMP_EPSILON = 1e-9;

export interface UnitSnapshot {
    pos: { x: number; y: number; z: number };
    hp: number;
    en: number;
    ammo: Record<string, number>;
    warnings: WarningType[];
    /** 現在の胴体向き（度数法）— BattleViewer向き矢印表示用 */
    heading?: number;
    /** 現在のターゲットMS ID — BattleViewer照準線・ハイライト表示用 */
    targetId?: string;
}

// 現在のタイムスタンプ時点での情報を計算する関数（Hookではない）
export function getBattleSnapshot(
    targetId: string,
    initialMs: MobileSuit,
    logs: BattleLog[],
    currentTimestamp: number
): UnitSnapshot {
    let pos = initialMs.position;
    let hp = initialMs.max_hp; // 戦闘開始時は満タンと仮定
    let en = initialMs.max_en || DEFAULT_MAX_EN;
    const ammo: Record<string, number> = {};
    const warnings: WarningType[] = [];
    let heading: number | undefined = undefined;
    let unitTargetId: string | undefined = undefined;
    
    // 武器の初期弾数を設定
    initialMs.weapons.forEach(weapon => {
        if (weapon.max_ammo !== null && weapon.max_ammo !== undefined) {
            ammo[weapon.id] = weapon.max_ammo;
        }
    });

    // 開始から現在タイムスタンプまでのログを走査して状態を再現
    for (const log of logs) {
        if (log.timestamp > currentTimestamp + TIMESTAMP_EPSILON) break;

        // 位置更新
        if (log.actor_id === targetId && log.position_snapshot) {
            pos = log.position_snapshot;
        }

        // 向き更新（自ユニットのログに heading フィールドがあれば取得）
        if (log.actor_id === targetId && log.heading !== undefined) {
            heading = log.heading;
        }

        // ターゲット更新（TARGET_SELECTION ログから現在のターゲットを追跡）
        if (log.actor_id === targetId && log.action_type === "TARGET_SELECTION" && log.target_id) {
            unitTargetId = log.target_id;
        }

        // HP更新
        if (log.action_type === "DAMAGE" && log.actor_id === targetId && log.damage) {
            hp -= log.damage;
        }
        if ((log.action_type === "ATTACK" || log.action_type === "MELEE_COMBO") && log.target_id === targetId && log.damage) {
            hp -= log.damage;
        }
        
        // リソース消費の推測（簡易版）
        // 注意: ログデータに武器情報が含まれていないため、最初の武器を使用したと仮定しています
        if (log.action_type === "ATTACK" && log.actor_id === targetId) {
            const weapon = initialMs.weapons[0]; // 簡略化: 最初の武器を使用と仮定
            if (weapon) {
                if (weapon.en_cost) {
                    en = Math.max(0, en - weapon.en_cost);
                }
                if (weapon.max_ammo && ammo[weapon.id] !== undefined) {
                    ammo[weapon.id] = Math.max(0, ammo[weapon.id] - 1);
                }
            }
        }
    }
    
    // 警告状態を判定
    // EN不足: EN_WARNING_THRESHOLD以下
    const maxEn = initialMs.max_en || DEFAULT_MAX_EN;
    if (maxEn > 0 && en / maxEn < EN_WARNING_THRESHOLD) {
        warnings.push('energy');
    }
    
    // 弾切れ: 第1武器の弾薬が0
    const firstWeapon = initialMs.weapons[0];
    if (firstWeapon && firstWeapon.max_ammo !== null && firstWeapon.max_ammo !== undefined) {
        if (ammo[firstWeapon.id] === 0) {
            warnings.push('ammo');
        }
    }
    
    // クールダウン判定（簡易版：最後の攻撃から一定時間以内）
    // 注: より正確な実装には武器ごとのクールダウン追跡が必要
    let lastAttackTimestamp = 0;
    for (let i = logs.length - 1; i >= 0; i--) {
        if (logs[i].action_type === "ATTACK" && logs[i].actor_id === targetId) {
            lastAttackTimestamp = logs[i].timestamp;
            break;
        }
    }
    // cool_down_turn を秒換算（1ターン = 0.1s）
    const cooldownSeconds = (firstWeapon?.cool_down_turn || 0) * 0.1;
    if (cooldownSeconds > 0 && currentTimestamp - lastAttackTimestamp < cooldownSeconds) {
        warnings.push('cooldown');
    }

    return { pos, hp: Math.max(0, hp), en, ammo, warnings, heading, targetId: unitTargetId };
}

/**
 * 指定タイムスタンプ時点でプレイヤーが索敵済みの敵MSのIDセットを返す。
 * バトルログから action_type === "DETECTION" かつ actor_id === playerId のエントリを収集する。
 * 索敵は永続的（一度発見したMSは以降も表示し続ける）。
 */
export function getDetectedUnits(
    playerId: string,
    logs: BattleLog[],
    currentTimestamp: number
): Set<string> {
    const detected = new Set<string>();
    for (const log of logs) {
        if (log.timestamp > currentTimestamp + TIMESTAMP_EPSILON) break;
        if (log.action_type === "DETECTION" && log.actor_id === playerId && log.target_id) {
            detected.add(log.target_id);
        }
    }
    return detected;
}
