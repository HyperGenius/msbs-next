/* frontend/src/components/BattleViewer/ui/BattleOverlay.tsx */

"use client";

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

interface BattleOverlayProps {
    player: MobileSuit;
    playerState: UnitState;
    enemyStates: Array<{ enemy: MobileSuit; state: UnitState }>;
    environment: string;
    currentTurn: number;
    logs: BattleLog[];
}

export function BattleOverlay({
    player,
    playerState,
    enemyStates,
    environment,
    currentTurn,
    logs,
}: BattleOverlayProps) {
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
                        currentTurn={currentTurn}
                        unitId={player.id}
                        logs={logs}
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
                {enemyStates.map(({ enemy, state }) => (
                    <div key={enemy.id} className="mt-1 sm:mt-2">
                        <span className="font-bold text-red-400 block truncate text-[10px] sm:text-xs">
                            {enemy.npc_pilot_level !== undefined && enemy.npc_pilot_level !== null && (
                                <span className="text-yellow-400 mr-1">Lv.{enemy.npc_pilot_level}</span>
                            )}
                            {enemy.name}
                        </span>
                        <span className="text-[9px] sm:text-xs">
                            HP: {state.hp} / {enemy.max_hp}
                        </span>
                        <HpBar 
                            current={state.hp} 
                            max={enemy.max_hp} 
                            colorFunc={getEnemyHpBarColor}
                            currentTurn={currentTurn}
                            unitId={enemy.id}
                            logs={logs}
                        />
                    </div>
                ))}
            </div>

            {/* Environment Label */}
            <div className="absolute top-1 right-1 sm:top-2 sm:right-2 text-white bg-black/60 px-2 sm:px-3 py-0.5 sm:py-1 text-[10px] sm:text-xs font-mono pointer-events-none rounded border border-green-900/50">
                <span className="text-green-400">環境:</span> {environment}
            </div>
        </>
    );
}
