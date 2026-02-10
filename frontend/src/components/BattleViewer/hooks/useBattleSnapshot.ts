/* frontend/src/components/BattleViewer/hooks/useBattleSnapshot.ts */

import { BattleLog, MobileSuit } from "@/types/battle";
import { DEFAULT_MAX_EN, EN_WARNING_THRESHOLD } from "../utils";
import { WarningType } from "../types";

interface UnitSnapshot {
    pos: { x: number; y: number; z: number };
    hp: number;
    en: number;
    ammo: Record<string, number>;
    warnings: WarningType[];
}

export function useBattleSnapshot(
    targetId: string,
    initialMs: MobileSuit,
    logs: BattleLog[],
    currentTurn: number
): UnitSnapshot {
    let pos = initialMs.position;
    let hp = initialMs.max_hp; // 戦闘開始時は満タンと仮定
    let en = initialMs.max_en || DEFAULT_MAX_EN;
    const ammo: Record<string, number> = {};
    const warnings: WarningType[] = [];
    
    // 武器の初期弾数を設定
    initialMs.weapons.forEach(weapon => {
        if (weapon.max_ammo !== null && weapon.max_ammo !== undefined) {
            ammo[weapon.id] = weapon.max_ammo;
        }
    });

    // 開始から現在ターンまでのログを走査して状態を再現
    for (const log of logs) {
        if (log.turn > currentTurn) break;

        // 位置更新
        if (log.actor_id === targetId && log.position_snapshot) {
            pos = log.position_snapshot;
        }

        // HP更新
        if (log.action_type === "DAMAGE" && log.actor_id === targetId && log.damage) {
            hp -= log.damage;
        }
        if (log.action_type === "ATTACK" && log.target_id === targetId && log.damage) {
            hp -= log.damage;
        }
        
        // リソース消費の推測（簡易版）
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
    
    // クールダウン判定（簡易版：最後の攻撃から一定ターン以内）
    let lastAttackTurn = 0;
    for (let i = logs.length - 1; i >= 0; i--) {
        if (logs[i].action_type === "ATTACK" && logs[i].actor_id === targetId) {
            lastAttackTurn = logs[i].turn;
            break;
        }
    }
    const cooldownTurns = firstWeapon?.cool_down_turn || 0;
    if (cooldownTurns > 0 && currentTurn - lastAttackTurn < cooldownTurns) {
        warnings.push('cooldown');
    }

    return { pos, hp: Math.max(0, hp), en, ammo, warnings };
}
