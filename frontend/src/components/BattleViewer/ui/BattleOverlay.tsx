/* frontend/src/components/BattleViewer/ui/BattleOverlay.tsx */

"use client";

import { RefObject, useEffect, useMemo, useRef } from "react";
import { BattleLog, MobileSuit } from "@/types/battle";
import { HpBar } from "./HpBar";
import { getHpBarColor, getEnemyHpBarColor, DEFAULT_MAX_EN, EN_WARNING_THRESHOLD, HIT_EFFECT_COLORS } from "../utils";
import { HudLogLine, useHudAttackLog } from "../hooks/useHudAttackLog";
import { findLatestEnShortageEvent, isEnShortageLog } from "../hooks/useBattleSnapshot";

interface UnitState {
    pos: { x: number; y: number; z: number };
    hp: number;
    en: number;
    ammo: Record<string, number>;
    warnings: string[];
}

/** ENゲージの点滅（Issue #534）。0.3s で 1 回、2 回繰り返す */
const EN_BLINK_KEYFRAMES: Keyframe[] = [{ opacity: 1 }, { opacity: 0.15 }, { opacity: 1 }];
const EN_BLINK_OPTIONS: KeyframeAnimationOptions = { duration: 300, iterations: 2, easing: "ease-in-out" };

/**
 * 再生位置が EN 不足イベントの時刻を通過したとき、target 要素を 2 回点滅させる。
 * 前回の再生位置は ref で持ち、React の state は更新しない（アニメーションは Web Animations API で直接再生する）。
 * 一時停止中は currentTimestamp が変わらないため発火せず、巻き戻したときは点滅を止めて過去のイベントでは発火させない。
 */
function useEnShortageBlink(
    target: RefObject<HTMLDivElement | null>,
    enShortageTimestamps: number[],
    currentTimestamp: number
) {
    const prevTimestampRef = useRef(currentTimestamp);
    const animationRef = useRef<Animation | null>(null);

    useEffect(() => {
        const prevTimestamp = prevTimestampRef.current;
        prevTimestampRef.current = currentTimestamp;
        if (currentTimestamp === prevTimestamp) return;

        if (currentTimestamp < prevTimestamp) {
            animationRef.current?.cancel();
            return;
        }
        if (findLatestEnShortageEvent(enShortageTimestamps, prevTimestamp, currentTimestamp) === null) return;
        // 点滅中に次のイベントが来たら、重ねずに最初から 2 回点滅し直す
        animationRef.current?.cancel();
        animationRef.current = target.current?.animate(EN_BLINK_KEYFRAMES, EN_BLINK_OPTIONS) ?? null;
    }, [target, enShortageTimestamps, currentTimestamp]);
}

/** 敵HPパネルに表示する敵機の最大数。超過分は「…他N機」で省略する（Issue #521） */
const MAX_VISIBLE_ENEMIES = 2;
const SELF_ATTACK_ACTION_TYPES = new Set(["ATTACK", "MELEE_COMBO", "MISS"]);
const HUD_LOG_LINES = 3;
// dealt は色を付けず、HUD 本文と同じ明るいグレー（text-gray-200）で出す
const HUD_LOG_TONE_COLOR: Record<HudLogLine["tone"], string | undefined> = {
    dealt: undefined,
    taken: HIT_EFFECT_COLORS.taken,
    miss: HIT_EFFECT_COLORS.miss,
};

interface BattleOverlayProps {
    player: MobileSuit;
    playerState: UnitState;
    enemyStates: Array<{ enemy: MobileSuit; state: UnitState }>;
    environment: string;
    currentTimestamp: number;
    /** 自機の現在ターゲット判定と HUD ログに使う全ログ */
    logs: BattleLog[];
    /** LOS 表示の現在の状態 */
    showLos: boolean;
    /** LOS 表示トグルのコールバック */
    onToggleLos: () => void;
}

export function BattleOverlay({
    player,
    playerState,
    enemyStates,
    environment,
    currentTimestamp,
    logs,
    showLos,
    onToggleLos,
}: BattleOverlayProps) {
    // 自機が攻撃対象にした敵ログのみを事前に抽出しておく（Issue #521）。currentTimestamp は
    // 再生中100msごとに変わるため、全ログの逆順走査を毎tick行うと大規模バトル（十万件規模の
    // ログ、docs/features/battle-log-feature.md参照）で重くなる。logs参照が変わらない限り
    // この絞り込み自体は再計算しない。
    const selfTargetLogs = useMemo(
        () =>
            logs.filter(
                (log) => log.actor_id === player.id && log.target_id && SELF_ATTACK_ACTION_TYPES.has(log.action_type)
            ),
        [logs, player.id]
    );

    const currentTargetId = useMemo(() => {
        for (let i = selfTargetLogs.length - 1; i >= 0; i--) {
            if (selfTargetLogs[i].timestamp <= currentTimestamp) {
                return selfTargetLogs[i].target_id ?? null;
            }
        }
        return null;
    }, [selfTargetLogs, currentTimestamp]);

    const sortedAliveEnemies = useMemo(() => {
        const alive = enemyStates.filter(({ state }) => state.hp > 0);
        const target = alive.filter(({ enemy }) => enemy.id === currentTargetId);
        const others = alive.filter(({ enemy }) => enemy.id !== currentTargetId);
        return [...target, ...others];
    }, [enemyStates, currentTargetId]);
    const visibleEnemies = sortedAliveEnemies.slice(0, MAX_VISIBLE_ENEMIES);
    const hiddenEnemyCount = sortedAliveEnemies.length - visibleEnemies.length;

    // 未索敵の敵は名前を引けないようにし、HUD ログにも出さない
    const unitNames = useMemo(() => {
        const names = new Map<string, string>([[player.id, player.name]]);
        enemyStates.forEach(({ enemy }) => names.set(enemy.id, enemy.name));
        return names;
    }, [player.id, player.name, enemyStates]);

    // EN不足イベント（Issue #534）。再生で時刻を通過したときだけ ENゲージを点滅させる
    const enShortageTimestamps = useMemo(
        () => logs.filter((log) => log.actor_id === player.id && isEnShortageLog(log)).map((log) => log.timestamp),
        [logs, player.id]
    );
    const enGaugeRef = useRef<HTMLDivElement>(null);
    useEnShortageBlink(enGaugeRef, enShortageTimestamps, currentTimestamp);

    const maxEn = player.max_en || DEFAULT_MAX_EN;
    const enRatio = maxEn > 0 ? playerState.en / maxEn : 0;
    const isEnLow = enRatio < EN_WARNING_THRESHOLD;

    const hudLogLines = useHudAttackLog({
        logs,
        currentTimestamp,
        names: unitNames,
        playerId: player.id,
        limit: HUD_LOG_LINES,
    });

    return (
        <>
            {/* UIオーバーレイ */}
            <div className="absolute top-1 left-1 sm:top-2 sm:left-2 text-white bg-black/60 p-1.5 sm:p-2 text-[10px] sm:text-xs font-mono pointer-events-none rounded border border-green-900/50 max-w-[45%]">
                <div className="mb-1 sm:mb-2 border-b border-blue-500/30 pb-1 sm:pb-2">
                    <span className="font-bold text-blue-400 block truncate">{player.name}</span>
                    <span className="text-[9px] sm:text-xs">
                        HP: {playerState.hp} / {player.max_hp}
                    </span>
                    <HpBar current={playerState.hp} max={player.max_hp} colorFunc={getHpBarColor} />
                    
                    {/* EN Display */}
                    <div className="mt-0.5 sm:mt-1">
                        <span className={`${isEnLow ? "text-red-400" : "text-cyan-400"} text-[9px] sm:text-xs transition-all duration-300`}>EN:</span>
                        <span className="text-[9px] sm:text-xs">{Math.round(playerState.en)} / {maxEn}</span>
                        <div
                            ref={enGaugeRef}
                            className="w-16 sm:w-24 h-1.5 sm:h-2 bg-gray-700 mt-0.5 sm:mt-1 rounded overflow-hidden border border-gray-600"
                        >
                            <div
                                className={`h-full ${isEnLow ? "bg-red-500" : "bg-cyan-500"} transition-all duration-300`}
                                style={{ width: `${Math.min(1, Math.max(0, enRatio)) * 100}%` }}
                            ></div>
                        </div>
                    </div>
                    
                    {/* Ammo Display */}
                    {player.weapons && player.weapons.length > 0 && player.weapons[0].max_ammo !== null && player.weapons[0].max_ammo !== undefined && (
                        <div className="mt-0.5 sm:mt-1">
                            <span className="text-orange-400 text-[9px] sm:text-xs">弾薬:</span> 
                            <span className="text-[9px] sm:text-xs">{playerState.ammo[player.weapons[0].id] || 0} / {player.weapons[0].max_ammo}</span>
                        </div>
                    )}
                </div>
                {visibleEnemies.map(({ enemy, state }) => (
                    <div key={enemy.id} className="mt-1 sm:mt-2">
                        <span className="font-bold text-red-400 block truncate text-[10px] sm:text-xs">
                            {enemy.id === currentTargetId && (
                                <span className="bg-yellow-400 text-black text-[8px] font-bold rounded px-1 mr-1 align-middle">TGT</span>
                            )}
                            {enemy.npc_pilot_level !== undefined && enemy.npc_pilot_level !== null && (
                                <span className="text-yellow-400 mr-1">Lv.{enemy.npc_pilot_level}</span>
                            )}
                            {enemy.name}
                        </span>
                        <HpBar current={state.hp} max={enemy.max_hp} colorFunc={getEnemyHpBarColor} />
                    </div>
                ))}
                {hiddenEnemyCount > 0 && (
                    <div className="mt-1 text-[9px] sm:text-[10px] text-gray-400 text-right">…他{hiddenEnemyCount}機</div>
                )}
            </div>

            {/* Environment Label */}
            <div className="absolute top-1 right-1 sm:top-2 sm:right-2 text-white bg-black/60 px-2 sm:px-3 py-0.5 sm:py-1 text-[10px] sm:text-xs font-mono pointer-events-none rounded border border-green-900/50">
                <span className="text-green-400">環境:</span> {environment}
            </div>

            {/* 直近の攻撃ログ。右下の LOS ボタンと重ならないよう幅を抑える */}
            {hudLogLines.length > 0 && (
                <div className="absolute bottom-1 left-1 sm:bottom-2 sm:left-2 max-w-[calc(100%-6rem)] bg-black/60 px-2 py-1 text-[9px] sm:text-xs font-mono text-gray-200 pointer-events-none rounded border border-green-900/50">
                    {hudLogLines.map((line, i) => {
                        const isLatest = i === hudLogLines.length - 1;
                        return (
                            <div
                                key={line.key}
                                className={`truncate ${isLatest ? "animate-fade-in" : "opacity-60"}`}
                                style={{ color: HUD_LOG_TONE_COLOR[line.tone], whiteSpace: "pre" }}
                            >
                                {line.text}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* LOS 表示トグルボタン */}
            <div className="absolute bottom-1 right-1 sm:bottom-2 sm:right-2">
                <button
                    onClick={onToggleLos}
                    className={`px-2 py-0.5 text-[10px] sm:text-xs font-mono rounded border transition-colors ${
                        showLos
                            ? "bg-green-900/80 border-green-500 text-green-300"
                            : "bg-black/60 border-green-900/50 text-gray-400"
                    }`}
                >
                    LOS: {showLos ? "ON" : "OFF"}
                </button>
            </div>
        </>
    );
}
