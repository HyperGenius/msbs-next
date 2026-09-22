/* frontend/src/components/BattleViewer/ui/BattleOverlay.tsx */

"use client";

import { useMemo } from "react";
import { BattleLog, MobileSuit } from "@/types/battle";
import { HpBar } from "./HpBar";
import { getHpBarColor, getEnemyHpBarColor, DEFAULT_MAX_EN } from "../utils";

interface UnitState {
    pos: { x: number; y: number; z: number };
    hp: number;
    en: number;
    ammo: Record<string, number>;
    warnings: string[];
}

/** 敵HPパネルに表示する敵機の最大数。超過分は「…他N機」で省略する（Issue #521） */
const MAX_VISIBLE_ENEMIES = 2;
const SELF_ATTACK_ACTION_TYPES = new Set(["ATTACK", "MELEE_COMBO", "MISS"]);

interface BattleOverlayProps {
    player: MobileSuit;
    playerState: UnitState;
    enemyStates: Array<{ enemy: MobileSuit; state: UnitState }>;
    environment: string;
    currentTimestamp: number;
    /** 現在タイムスタンプ分にフィルタ済みのログ（呼び出し元で計算済み。Issue #467） */
    timestampLogs: BattleLog[];
    /** 自機の現在ターゲット判定用の全ログ（Issue #521） */
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
    timestampLogs,
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

    return (
        <>
            {/* UIオーバーレイ */}
            <div className="absolute top-1 left-1 sm:top-2 sm:left-2 text-white bg-black/60 p-1.5 sm:p-2 text-[10px] sm:text-xs font-mono pointer-events-none rounded border border-green-900/50 max-w-[45%]">
                <div className="mb-1 sm:mb-2 border-b border-blue-500/30 pb-1 sm:pb-2">
                    <span className="font-bold text-blue-400 block truncate">{player.name}</span>
                    <span className="text-[9px] sm:text-xs">
                        HP: {playerState.hp} / {player.max_hp}
                    </span>
                    <HpBar 
                        current={playerState.hp} 
                        max={player.max_hp} 
                        colorFunc={getHpBarColor}
                        currentTimestamp={currentTimestamp}
                        unitId={player.id}
                        timestampLogs={timestampLogs}
                    />
                    
                    {/* EN Display */}
                    <div className="mt-0.5 sm:mt-1">
                        <span className="text-cyan-400 text-[9px] sm:text-xs">EN:</span> 
                        <span className="text-[9px] sm:text-xs">{playerState.en} / {player.max_en || DEFAULT_MAX_EN}</span>
                        <div className="w-16 sm:w-24 h-1.5 sm:h-2 bg-gray-700 mt-0.5 sm:mt-1 rounded overflow-hidden border border-gray-600">
                            <div 
                                className="h-full bg-cyan-500 transition-all duration-300" 
                                style={{ width: `${(playerState.en / (player.max_en || DEFAULT_MAX_EN)) * 100}%` }}
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
                        <HpBar
                            current={state.hp}
                            max={enemy.max_hp}
                            colorFunc={getEnemyHpBarColor}
                            currentTimestamp={currentTimestamp}
                            unitId={enemy.id}
                            timestampLogs={timestampLogs}
                        />
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
