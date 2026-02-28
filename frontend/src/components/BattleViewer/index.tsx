/* frontend/src/components/BattleViewer/index.tsx */

"use client";

import { BattleLog, MobileSuit } from "@/types/battle";
import { getBattleSnapshot } from "./hooks/useBattleSnapshot";
import { useBattleEvents } from "./hooks/useBattleEvents";
import { BattleScene } from "./scene/BattleScene";
import { BattleOverlay } from "./ui/BattleOverlay";
import { getEnvironmentColor } from "./utils";

interface BattleViewerProps {
    logs: BattleLog[];
    player: MobileSuit;
    enemies: MobileSuit[];
    currentTurn: number;
    environment?: string;
}

export default function BattleViewer({ 
    logs, 
    player, 
    enemies, 
    currentTurn, 
    environment = "SPACE" 
}: BattleViewerProps) {
    // 状態計算（純粋関数として抽出）
    const playerSnapshot = getBattleSnapshot(player.id, player, logs, currentTurn);
    const playerPrevSnapshot = getBattleSnapshot(player.id, player, logs, currentTurn - 1);
    const playerState = { ...playerSnapshot, prevHp: playerPrevSnapshot.hp };

    const enemyStates = enemies.map(enemy => {
        const snapshot = getBattleSnapshot(enemy.id, enemy, logs, currentTurn);
        const prevSnapshot = getBattleSnapshot(enemy.id, enemy, logs, currentTurn - 1);
        return { enemy, state: { ...snapshot, prevHp: prevSnapshot.hp } };
    });
    
    // バトルイベントの取得
    const battleEventMap = useBattleEvents(logs, currentTurn);
    
    const playerEvent = battleEventMap.get(player.id) || null;
    const enemyEvents = enemies.map(enemy => ({
        id: enemy.id,
        event: battleEventMap.get(enemy.id) || null
    }));

    return (
        <div 
            className="w-full h-[300px] sm:h-[400px] md:h-[500px] rounded border border-green-800 mb-4 overflow-hidden relative touch-none" 
            style={{ backgroundColor: getEnvironmentColor(environment) }}
        >
            <BattleScene
                environment={environment}
                player={player}
                playerState={playerState}
                playerEvent={playerEvent}
                enemyStates={enemyStates}
                enemyEvents={enemyEvents}
            />
            
            <BattleOverlay
                player={player}
                playerState={playerState}
                enemyStates={enemyStates}
                environment={environment}
                currentTurn={currentTurn}
                logs={logs}
            />
        </div>
    );
}
