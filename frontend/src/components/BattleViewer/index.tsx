/* frontend/src/components/BattleViewer/index.tsx */

"use client";

import { BattleLog, MobileSuit, Obstacle } from "@/types/battle";
import { getBattleSnapshot, getDetectedUnits } from "./hooks/useBattleSnapshot";
import { useBattleEvents } from "./hooks/useBattleEvents";
import { BattleScene } from "./scene/BattleScene";
import { BattleOverlay } from "./ui/BattleOverlay";
import { ComboEffect } from "./ui/ComboEffect";
import { getEnvironmentColor, SIMULATION_STEP_S } from "./utils";
import { IS_PRODUCTION } from "@/constants";

interface BattleViewerProps {
    logs: BattleLog[];
    player: MobileSuit;
    enemies: MobileSuit[];
    obstacles?: Obstacle[];
    currentTimestamp: number;
    environment?: string;
}

export default function BattleViewer({ 
    logs, 
    player, 
    enemies, 
    obstacles,
    currentTimestamp, 
    environment = "SPACE" 
}: BattleViewerProps) {
    // 状態計算（純粋関数として抽出）
    const playerSnapshot = getBattleSnapshot(player.id, player, logs, currentTimestamp);
    const playerPrevSnapshot = getBattleSnapshot(player.id, player, logs, currentTimestamp - SIMULATION_STEP_S);
    const playerState = { ...playerSnapshot, prevHp: playerPrevSnapshot.hp };

    const enemyStates = enemies.map(enemy => {
        const snapshot = getBattleSnapshot(enemy.id, enemy, logs, currentTimestamp);
        const prevSnapshot = getBattleSnapshot(enemy.id, enemy, logs, currentTimestamp - SIMULATION_STEP_S);
        return { enemy, state: { ...snapshot, prevHp: prevSnapshot.hp } };
    });

    // 本番環境では索敵済み敵MSのみ表示（開発環境では全MS表示）
    const detectedIds = IS_PRODUCTION
        ? getDetectedUnits(player.id, logs, currentTimestamp)
        : null;
    const visibleEnemyStates = detectedIds
        ? enemyStates.filter(({ enemy }) => detectedIds.has(enemy.id))
        : enemyStates;
    
    // バトルイベントの取得
    const battleEventMap = useBattleEvents(logs, currentTimestamp);
    
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
                enemyStates={visibleEnemyStates}
                enemyEvents={enemyEvents}
                obstacles={obstacles}
            />
            
            <BattleOverlay
                player={player}
                playerState={playerState}
                enemyStates={visibleEnemyStates}
                environment={environment}
                currentTimestamp={currentTimestamp}
                logs={logs}
            />

            {/* 格闘コンボエフェクト (Phase C) */}
            <ComboEffect logs={logs} currentTimestamp={currentTimestamp} />
        </div>
    );
}
