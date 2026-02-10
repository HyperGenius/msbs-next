/* frontend/src/components/BattleViewer/hooks/useBattleEvents.ts */

import { useMemo } from "react";
import { BattleLog } from "@/types/battle";
import { BattleEventEffect } from "../types";
import { RESIST_PATTERN } from "../utils";

export function useBattleEvents(
    logs: BattleLog[],
    currentTurn: number,
    unitIds: string[]
): Map<string, BattleEventEffect | null> {
    return useMemo(() => {
        const currentTurnLogs = logs.filter(log => log.turn === currentTurn);
        const battleEventMap = new Map<string, BattleEventEffect | null>();
        
        for (const log of currentTurnLogs) {
            // クリティカルヒット検出
            if (log.action_type === "ATTACK" && log.actor_id && 
                log.message.includes("クリティカルヒット") && !battleEventMap.has(log.actor_id)) {
                battleEventMap.set(log.actor_id, {
                    type: 'critical',
                    text: 'CRITICAL HIT!!',
                    color: '#ff0000'
                });
            }
            
            // 防御/軽減検出（ダメージを受けた側）
            if (log.action_type === "ATTACK" && log.target_id && !battleEventMap.has(log.target_id)) {
                if (log.message.includes("対ビーム装甲により") || log.message.includes("対実弾装甲により")) {
                    const resistMatch = log.message.match(RESIST_PATTERN);
                    const percent = resistMatch ? resistMatch[1] : '';
                    battleEventMap.set(log.target_id, {
                        type: 'resist',
                        text: `RESIST ${percent}%`,
                        color: '#4caf50'
                    });
                } else if (log.damage && log.damage > 0) {
                    // 通常ダメージの場合、ダメージ数値を表示
                    battleEventMap.set(log.target_id, {
                        type: 'damage',
                        text: `-${log.damage}`,
                        color: '#ff5722'
                    });
                }
            }
        }
        
        return battleEventMap;
    }, [logs, currentTurn]);
}
