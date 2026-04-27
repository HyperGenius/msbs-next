/* frontend/src/components/BattleViewer/ui/HpBar.tsx */

"use client";

import { useState, useEffect, useRef } from "react";
import { BattleLog } from "@/types/battle";

// HPバーコンポーネント（ダメージフラッシュ効果付き）
export function HpBar({ 
    current, 
    max, 
    colorFunc, 
    currentTimestamp,
    unitId,
    logs
}: { 
    current: number; 
    max: number; 
    colorFunc: (ratio: number) => string;
    currentTimestamp: number;
    unitId: string;
    logs: BattleLog[];
}) {
    const [flash, setFlash] = useState(false);
    const prevTimestampRef = useRef(currentTimestamp);
    
    useEffect(() => {
        // タイムスタンプが変わったときにダメージを受けたかチェック
        if (currentTimestamp !== prevTimestampRef.current) {
            const timestampLogs = logs.filter(log => Math.abs(log.timestamp - currentTimestamp) < 1e-9);
            const tookDamage = timestampLogs.some(log => 
                (log.action_type === "ATTACK" && log.target_id === unitId && log.damage && log.damage > 0) ||
                (log.action_type === "DAMAGE" && log.actor_id === unitId && log.damage && log.damage > 0)
            );
            
            if (tookDamage) {
                // Note: This is intentional for triggering damage flash animation
                // eslint-disable-next-line react-hooks/set-state-in-effect
                setFlash(true);
                setTimeout(() => setFlash(false), 300);
            }
            
            prevTimestampRef.current = currentTimestamp;
        }
    }, [currentTimestamp, unitId, logs]);
    
    const ratio = current / max;
    const bgColor = colorFunc(ratio);
    
    return (
        <div className="w-24 h-2 bg-gray-700 mt-1 rounded overflow-hidden border border-gray-600 relative">
            <div 
                className={`h-full transition-all duration-300 ${flash ? 'animate-pulse' : ''}`}
                style={{ 
                    width: `${ratio * 100}%`,
                    backgroundColor: bgColor,
                    boxShadow: flash ? `0 0 8px ${bgColor}` : 'none'
                }}
            ></div>
        </div>
    );
}
