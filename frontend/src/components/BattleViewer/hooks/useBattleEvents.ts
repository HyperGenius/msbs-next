/* frontend/src/components/BattleViewer/hooks/useBattleEvents.ts */

import { useMemo } from "react";
import { BattleLog } from "@/types/battle";
import { BattleEventEffect } from "../types";
import { RESIST_PATTERN } from "../utils";

export function useBattleEvents(
    logs: BattleLog[],
    currentTimestamp: number
): Map<string, BattleEventEffect | null> {
    return useMemo(() => {
        const currentTimestampLogs = logs.filter(log => Math.abs(log.timestamp - currentTimestamp) < 1e-9);
        const battleEventMap = new Map<string, BattleEventEffect | null>();

        // Pass 1: ユニットの位置マップを構築（攻撃ライン描画のターゲット座標取得用）
        const positionMap = new Map<string, { x: number; y: number; z: number }>();
        for (const log of currentTimestampLogs) {
            if (log.actor_id && log.position_snapshot) {
                positionMap.set(log.actor_id, log.position_snapshot);
            }
        }

        // Pass 2: イベントエフェクトを生成
        for (const log of currentTimestampLogs) {
            // クリティカルヒット検出（アクター側に表示 + 攻撃ライン情報を付加）
            if (log.action_type === "ATTACK" && log.actor_id &&
                log.message.includes("クリティカルヒット") && !battleEventMap.has(log.actor_id)) {
                const targetPos = log.target_id ? positionMap.get(log.target_id) : undefined;
                battleEventMap.set(log.actor_id, {
                    type: 'critical',
                    text: '💥💥 CRITICAL HIT!!',
                    color: '#ff0000',
                    weaponName: log.weapon_name,
                    targetPos,
                    hit: true,
                });
            }

            // 格闘コンボ検出 (Phase C) — MELEE_COMBO ログはアクター側にエフェクト表示
            if (log.action_type === "MELEE_COMBO" && log.actor_id && !battleEventMap.has(log.actor_id)) {
                const comboCount = log.combo_count ?? 1;
                const color = comboCount >= 3 ? '#ff2200' : comboCount === 2 ? '#ff7700' : '#ffdd00';
                battleEventMap.set(log.actor_id, {
                    type: 'critical',
                    text: `${comboCount}HIT COMBO!!`,
                    color,
                    weaponName: log.weapon_name,
                });
            }

            // 格闘コンボのターゲットダメージ（action_type に依存しない統一処理）
            if (log.action_type === "MELEE_COMBO" && log.target_id && !battleEventMap.has(log.target_id)) {
                if (log.damage && log.damage > 0) {
                    battleEventMap.set(log.target_id, {
                        type: 'damage',
                        text: `💥 -${log.damage}`,
                        color: '#ff5722',
                        weaponName: log.weapon_name,
                    });
                }
            }

            // 防御/軽減検出（ダメージを受けた側）
            if (log.action_type === "ATTACK" && log.target_id && !battleEventMap.has(log.target_id)) {
                if (log.message.includes("対ビーム装甲により") || log.message.includes("対実弾装甲により")) {
                    const resistMatch = log.message.match(RESIST_PATTERN);
                    const percent = resistMatch ? resistMatch[1] : '';
                    battleEventMap.set(log.target_id, {
                        type: 'resist',
                        text: `RESIST ${percent}%`,
                        color: '#4caf50',
                        weaponName: log.weapon_name,
                    });
                } else if (log.message.includes("クリティカルヒット") && log.damage && log.damage > 0) {
                    // クリティカルダメージはターゲット側にも大きく表示
                    battleEventMap.set(log.target_id, {
                        type: 'critical',
                        text: `💥💥 -${log.damage}`,
                        color: '#ff0000',
                        weaponName: log.weapon_name,
                    });
                } else if (log.damage && log.damage > 0) {
                    // 通常ダメージ
                    battleEventMap.set(log.target_id, {
                        type: 'damage',
                        text: `💥 -${log.damage}`,
                        color: '#ffcc00',
                        weaponName: log.weapon_name,
                    });
                }
            }

            // ATTACK アクター側 → 攻撃ライン（命中）
            // クリティカル/コンボで既にアクター効果が設定済みの場合、targetPos を付加してライン描画も行う
            if (log.action_type === "ATTACK" && log.actor_id && log.target_id) {
                const targetPos = positionMap.get(log.target_id);
                if (targetPos) {
                    const existing = battleEventMap.get(log.actor_id);
                    if (existing) {
                        if (!existing.targetPos) {
                            battleEventMap.set(log.actor_id, { ...existing, targetPos, hit: true });
                        }
                    } else {
                        // 通常ATTACK: アクターに attack_line エフェクトを設定
                        battleEventMap.set(log.actor_id, {
                            type: 'attack_line',
                            text: '',
                            color: '#ffcc00',
                            weaponName: log.weapon_name,
                            targetPos,
                            hit: true,
                        });
                    }
                }
            }

            // MISS → アクターに attack_line（ミス）、ターゲットにミスエフェクト
            if (log.action_type === "MISS" && log.actor_id && log.target_id) {
                const targetPos = positionMap.get(log.target_id);
                if (targetPos && !battleEventMap.has(log.actor_id)) {
                    battleEventMap.set(log.actor_id, {
                        type: 'attack_line',
                        text: '',
                        color: '#888888',
                        weaponName: log.weapon_name,
                        targetPos,
                        hit: false,
                    });
                }
                if (!battleEventMap.has(log.target_id)) {
                    battleEventMap.set(log.target_id, {
                        type: 'miss',
                        text: '💨 MISS',
                        color: '#888888',
                        weaponName: log.weapon_name,
                    });
                }
            }
        }

        return battleEventMap;
    }, [logs, currentTimestamp]);
}
