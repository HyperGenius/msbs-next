/* frontend/src/components/BattleViewer/__stories__/EffectReplayStage.tsx */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import BattleViewer from "..";
import { EffectScenario } from "./battleLogFixtures";

interface EffectReplayStageProps {
    scenario: EffectScenario;
    environment: string;
    /** 自動リプレイの間隔（ms）。0 以下で自動リプレイを止める。 */
    replayIntervalMs: number;
}

// 0 秒に戻してから演出時刻へ進めるまでの待ち時間。
// 同じレンダーで往復させると BattleScene の useEffect([currentTimestamp]) が発火しない。
const REWIND_DELAY_MS = 150;

/** 1 件の演出シナリオを、0 秒と演出時刻の往復で繰り返し再生する。 */
export function EffectReplayStage({ scenario, environment, replayIntervalMs }: EffectReplayStageProps) {
    const { logs, player, enemies, eventTimestamp } = scenario;
    const [currentTimestamp, setCurrentTimestamp] = useState(0);
    const [replayCount, setReplayCount] = useState(0);
    const rewindTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const replay = useCallback(() => {
        if (rewindTimerRef.current) clearTimeout(rewindTimerRef.current);
        setCurrentTimestamp(0);
        rewindTimerRef.current = setTimeout(() => {
            setCurrentTimestamp(eventTimestamp);
            setReplayCount((c) => c + 1);
        }, REWIND_DELAY_MS);
    }, [eventTimestamp]);

    // シナリオが変わるたび（Controls 操作時）に即座に 1 回再生する
    useEffect(() => {
        const id = setTimeout(replay, 0);
        return () => clearTimeout(id);
    }, [replay, logs]);

    useEffect(() => {
        if (replayIntervalMs <= 0) return;
        const id = setInterval(replay, replayIntervalMs);
        return () => clearInterval(id);
    }, [replay, replayIntervalMs]);

    useEffect(() => () => {
        if (rewindTimerRef.current) clearTimeout(rewindTimerRef.current);
    }, []);

    return (
        <div className="p-4 max-w-3xl mx-auto">
            <BattleViewer
                logs={logs}
                player={player}
                enemies={enemies}
                currentTimestamp={currentTimestamp}
                environment={environment}
            />
            <div className="flex items-center gap-4 text-xs text-green-400">
                <button
                    type="button"
                    onClick={replay}
                    className="px-3 py-1 border border-[#00ff41] text-[#00ff41] bg-transparent hover:bg-[#00ff41] hover:text-black"
                >
                    ▶ Replay
                </button>
                <span>t = {currentTimestamp.toFixed(1)}s</span>
                <span>再生回数: {replayCount}</span>
                <span>{replayIntervalMs > 0 ? `自動リプレイ: ${replayIntervalMs}ms 毎` : "自動リプレイ: OFF"}</span>
            </div>
        </div>
    );
}
