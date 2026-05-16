/* frontend/src/components/BattleViewer/index.tsx */

"use client";

import { useMemo, useState } from "react";
import { BattleLog, MobileSuit, Obstacle } from "@/types/battle";
import { getBattleSnapshot, getDetectedUnits } from "./hooks/useBattleSnapshot";
import { useBattleEvents } from "./hooks/useBattleEvents";
import { BattleScene } from "./scene/BattleScene";
import { BattleOverlay } from "./ui/BattleOverlay";
import { ComboEffect } from "./ui/ComboEffect";
import { getEnvironmentColor, SIMULATION_STEP_S } from "./utils";
import { hasLos } from "./utils/losUtils";

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
    // LOS 表示のトグルステート（デフォルト: OFF）
    const [showLos, setShowLos] = useState(false);

    // 状態計算（純粋関数として抽出）
    const playerSnapshot = getBattleSnapshot(player.id, player, logs, currentTimestamp);
    const playerPrevSnapshot = getBattleSnapshot(player.id, player, logs, currentTimestamp - SIMULATION_STEP_S);
    const playerState = { ...playerSnapshot, prevHp: playerPrevSnapshot.hp };

    const enemyStates = enemies.map(enemy => {
        const snapshot = getBattleSnapshot(enemy.id, enemy, logs, currentTimestamp);
        const prevSnapshot = getBattleSnapshot(enemy.id, enemy, logs, currentTimestamp - SIMULATION_STEP_S);
        return { enemy, state: { ...snapshot, prevHp: prevSnapshot.hp } };
    });

    // 索敵済み敵MSのみ表示
    const detectedIds = getDetectedUnits(player.id, logs, currentTimestamp);
    const visibleEnemyStates = enemyStates.filter(({ enemy }) => detectedIds.has(enemy.id));
    
    // バトルイベントの取得
    const battleEventMap = useBattleEvents(logs, currentTimestamp);
    
    const playerEvent = battleEventMap.get(player.id) || null;
    const enemyEvents = enemies.map(enemy => ({
        id: enemy.id,
        event: battleEventMap.get(enemy.id) || null
    }));

    // LOS 計算（currentTimestamp 変更時のみ再計算、showLos が OFF のときはスキップ）
    const losResults = useMemo(() => {
        if (!showLos) return undefined;
        const obs = obstacles ?? [];
        return visibleEnemyStates
            .filter(({ state }) => state.hp > 0)
            .map(({ enemy, state }) => {
                const result = hasLos(playerState.pos, state.pos, obs);
                return {
                    enemyId: enemy.id,
                    clear: result.clear,
                    blockedBy: result.blockedBy,
                    playerPos: playerState.pos,
                    enemyPos: state.pos,
                };
            });
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [showLos, currentTimestamp, obstacles]);

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
                losResults={losResults}
            />
            
            <BattleOverlay
                player={player}
                playerState={playerState}
                enemyStates={visibleEnemyStates}
                environment={environment}
                currentTimestamp={currentTimestamp}
                logs={logs}
                showLos={showLos}
                onToggleLos={() => setShowLos(v => !v)}
            />

            {/* 格闘コンボエフェクト (Phase C) */}
            <ComboEffect logs={logs} currentTimestamp={currentTimestamp} />
        </div>
    );
}
