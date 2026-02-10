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
            <div className="absolute top-2 left-2 text-white bg-black/60 p-2 text-xs font-mono pointer-events-none rounded border border-green-900/50">
                <div className="mb-2 border-b border-blue-500/30 pb-2">
                    <span className="font-bold text-blue-400">{player.name}</span>
                    <br />
                    HP: {playerState.hp} / {player.max_hp}
                    <HpBar 
                        current={playerState.hp} 
                        max={player.max_hp} 
                        colorFunc={getHpBarColor}
                        currentTurn={currentTurn}
                        unitId={player.id}
                        logs={logs}
                    />
                    
                    {/* EN Display */}
                    <div className="mt-1">
                        <span className="text-cyan-400">EN:</span> {playerState.en} / {player.max_en || DEFAULT_MAX_EN}
                        <div className="w-24 h-2 bg-gray-700 mt-1 rounded overflow-hidden border border-gray-600">
                            <div 
                                className="h-full bg-cyan-500 transition-all duration-300" 
                                style={{ width: `${(playerState.en / (player.max_en || DEFAULT_MAX_EN)) * 100}%` }}
                            ></div>
                        </div>
                    </div>
                    
                    {/* Ammo Display */}
                    {player.weapons && player.weapons.length > 0 && player.weapons[0].max_ammo !== null && player.weapons[0].max_ammo !== undefined && (
                        <div className="mt-1">
                            <span className="text-orange-400">弾薬:</span> {playerState.ammo[player.weapons[0].id] || 0} / {player.weapons[0].max_ammo}
                        </div>
                    )}
                </div>
                {enemyStates.map(({ enemy, state }) => (
                    <div key={enemy.id} className="mt-2">
                        <span className="font-bold text-red-400">{enemy.name}</span>
                        <br />
                        HP: {state.hp} / {enemy.max_hp}
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
            <div className="absolute top-2 right-2 text-white bg-black/60 px-3 py-1 text-xs font-mono pointer-events-none rounded border border-green-900/50">
                <span className="text-green-400">環境:</span> {environment}
            </div>
        </>
    );
}
