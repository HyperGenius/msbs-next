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
    const playerState = getBattleSnapshot(player.id, player, logs, currentTurn);
    const enemyStates = enemies.map(enemy => ({
        enemy,
        state: getBattleSnapshot(enemy.id, enemy, logs, currentTurn)
    }));
    
    // バトルイベントの取得
    const battleEventMap = useBattleEvents(logs, currentTurn);
    
    const playerEvent = battleEventMap.get(player.id) || null;
    const enemyEvents = enemies.map(enemy => ({
        id: enemy.id,
        event: battleEventMap.get(enemy.id) || null
    }));

    return (
        <div 
            className="w-full h-[400px] rounded border border-green-800 mb-4 overflow-hidden relative" 
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
