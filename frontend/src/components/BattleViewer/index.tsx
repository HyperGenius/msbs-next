/* frontend/src/components/BattleViewer/index.tsx */

"use client";

import { useMemo, useRef, useState } from "react";
import { BattleLog, MobileSuit, Obstacle } from "@/types/battle";
import { getBattleSnapshot, getDetectedUnits, SnapshotCache } from "./hooks/useBattleSnapshot";
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
    /** フィールド範囲 [min, max] (m)。BattleViewerの背景グリッド整列用 (Issue #436) */
    mapBounds?: [number, number] | null;
    currentTimestamp: number;
    environment?: string;
}

export default function BattleViewer({
    logs,
    player,
    enemies,
    obstacles,
    mapBounds,
    currentTimestamp,
    environment = "SPACE"
}: BattleViewerProps) {
    // LOS 表示のトグルステート（デフォルト: OFF）
    const [showLos, setShowLos] = useState(false);

    // getBattleSnapshot の差分更新キャッシュ（Issue #465）。
    // 再生（100ms毎の再レンダー）中は前回スキャン位置から続きだけを走査するため、
    // コンポーネントインスタンスを跨いで同じ Map を使い回す必要がある。
    // "現在時刻" 用と "1ステップ前" 用でキーを分け、両者が独立して単調に進行できるようにする。
    const snapshotCacheRef = useRef<SnapshotCache>(new Map());
    // BattleDetailModal 等はコンポーネントを再マウントせずに別バトルの logs を渡す場合があるため、
    // logs 参照が変わったらキャッシュを丸ごと作り直し、旧バトル分のエントリがMapに残り続けて
    // メモリが増え続けるのを防ぐ
    const lastLogsRef = useRef<BattleLog[] | null>(null);
    if (lastLogsRef.current !== logs) {
        snapshotCacheRef.current = new Map();
        lastLogsRef.current = logs;
    }
    const snapshotCache = snapshotCacheRef.current;

    // 状態計算（純粋関数として抽出）。currentTimestamp は再生クロックにより100msごとに更新されるため、
    // 実際に必要な依存値が変化していない限り再計算しないよう useMemo でメモ化する（Issue #466）
    const playerState = useMemo(() => {
        const snapshot = getBattleSnapshot(player.id, player, logs, currentTimestamp, snapshotCache);
        const prevSnapshot = getBattleSnapshot(player.id, player, logs, currentTimestamp - SIMULATION_STEP_S, snapshotCache, `${player.id}:prev`);
        return { ...snapshot, prevHp: prevSnapshot.hp };
    }, [player, logs, currentTimestamp, snapshotCache]);

    const enemyStates = useMemo(() => enemies.map(enemy => {
        const snapshot = getBattleSnapshot(enemy.id, enemy, logs, currentTimestamp, snapshotCache);
        const prevSnapshot = getBattleSnapshot(enemy.id, enemy, logs, currentTimestamp - SIMULATION_STEP_S, snapshotCache, `${enemy.id}:prev`);
        return { enemy, state: { ...snapshot, prevHp: prevSnapshot.hp } };
    }), [enemies, logs, currentTimestamp, snapshotCache]);

    // 索敵済み敵MSのみ表示
    const detectedIds = useMemo(
        () => getDetectedUnits(player.id, logs, currentTimestamp),
        [player.id, logs, currentTimestamp]
    );
    const visibleEnemyStates = useMemo(
        () => enemyStates.filter(({ enemy }) => detectedIds.has(enemy.id)),
        [enemyStates, detectedIds]
    );
    
    // 現在タイムスタンプ分のログ。useBattleEvents と BattleOverlay(HpBar) の両方が同じ
    // フィルタ結果を必要とするため、ここで一度だけ計算して共有する（Issue #467）
    const timestampLogs = useMemo(
        () => logs.filter(log => Math.abs(log.timestamp - currentTimestamp) < 1e-9),
        [logs, currentTimestamp]
    );

    // バトルイベントの取得（攻撃中ユニット ID セットを含む）(Issue #365)
    const { events: battleEventMap, attackingUnitIds } = useBattleEvents(timestampLogs);

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
                mapBounds={mapBounds}
                losResults={losResults}
                attackingUnitIds={attackingUnitIds}
                currentTimestamp={currentTimestamp}
            />
            
            <BattleOverlay
                player={player}
                playerState={playerState}
                enemyStates={visibleEnemyStates}
                environment={environment}
                currentTimestamp={currentTimestamp}
                timestampLogs={timestampLogs}
                showLos={showLos}
                onToggleLos={() => setShowLos(v => !v)}
            />

            {/* 格闘コンボエフェクト (Phase C) */}
            <ComboEffect logs={logs} currentTimestamp={currentTimestamp} />
        </div>
    );
}
