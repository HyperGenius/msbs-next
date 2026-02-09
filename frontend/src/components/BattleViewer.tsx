/* frontend/src/components/BattleViewer.tsx */
"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars, Grid } from "@react-three/drei";
import { BattleLog, MobileSuit } from "@/types/battle";
import * as THREE from "three";

// 色計算用のヘルパー
function getHpColor(current: number, max: number) {
    const ratio = current / max;
    if (ratio > 0.5) return "green"; // 余裕
    if (ratio > 0.2) return "yellow"; // 注意
    return "red"; // 危険
}

// デフォルト値定数
const DEFAULT_MAX_EN = 1000;

// MSを表示する球体コンポーネント
function MobileSuitMesh({
    position,
    maxHp,
    currentHp,
    sensorRange,
    showSensorRange,
}: {
    position: { x: number; y: number; z: number };
    maxHp: number;
    currentHp: number;
    name: string;
    sensorRange?: number;
    showSensorRange?: boolean;
}) {
    const scale = 0.05;
    const vec = new THREE.Vector3(position.x * scale, position.z * scale, position.y * scale);
    const color = getHpColor(currentHp, maxHp);

    return (
        <group position={vec}>
            <mesh scale={[2, 2, 2]}>
                <sphereGeometry args={[0.5, 32, 32]} />
                {/* 修正箇所: metalnessを下げ、emissive(発光)を追加 */}
                <meshStandardMaterial
                    color={color}
                    roughness={0.5}   // 表面を少しマットにする
                    metalness={0.1}   // 金属感を下げる（これで地の色が見えます）
                    emissive={color}  // 色と同じ色で少し発光させる
                    emissiveIntensity={0.3} // 発光強度

                />
            </mesh>
            
            {/* Sensor Range Visualization */}
            {showSensorRange && sensorRange && (
                <mesh position={[0, -1.8, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                    <ringGeometry args={[sensorRange * scale * 0.95, sensorRange * scale, 32]} />
                    <meshBasicMaterial color="#00ff00" transparent opacity={0.2} side={THREE.DoubleSide} />
                </mesh>
            )}
        </group>
    );
}

interface BattleViewerProps {
    logs: BattleLog[];
    player: MobileSuit;
    enemies: MobileSuit[];
    currentTurn: number;
    environment?: string;
}

// 環境エフェクトコンポーネント（外部で定義）
function EnvironmentEffects({ environment }: { environment: string }) {
    const getFogColor = () => {
        switch (environment) {
            case "GROUND":
                return "#2a5a2a"; // 緑系の霧
            case "COLONY":
                return "#4a4a6a"; // 紫系の霧
            case "UNDERWATER":
                return "#1a4a6a"; // 青系の霧
            case "SPACE":
            default:
                return "#000000"; // 霧なし
        }
    };
    
    const fogColor = getFogColor();
    
    switch (environment) {
        case "GROUND":
            return (
                <>
                    <fog attach="fog" args={[fogColor, 20, 100]} />
                    {/* 地面の表現 */}
                    <mesh position={[0, -2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshStandardMaterial color="#2a3a2a" roughness={0.9} />
                    </mesh>
                </>
            );
        case "COLONY":
            return (
                <>
                    <fog attach="fog" args={[fogColor, 30, 120]} />
                </>
            );
        case "UNDERWATER":
            return (
                <>
                    <fog attach="fog" args={[fogColor, 15, 80]} />
                    {/* 水面エフェクト（簡易版） */}
                    <mesh position={[0, 10, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshStandardMaterial 
                            color="#1a4a6a" 
                            transparent 
                            opacity={0.3} 
                            roughness={0.1}
                            metalness={0.8}
                        />
                    </mesh>
                </>
            );
        case "SPACE":
        default:
            return null;
    }
}

export default function BattleViewer({ logs, player, enemies, currentTurn, environment = "SPACE" }: BattleViewerProps) {

    // 現在のターン時点での情報を計算する関数
    const getSnapshot = (targetId: string, initialMs: MobileSuit) => {
        let pos = initialMs.position;
        let hp = initialMs.max_hp; // 戦闘開始時は満タンと仮定（あるいはinitialMs.current_hp）
        let en = initialMs.max_en || DEFAULT_MAX_EN;
        const ammo: Record<string, number> = {};
        
        // 武器の初期弾数を設定
        initialMs.weapons.forEach(weapon => {
            if (weapon.max_ammo !== null && weapon.max_ammo !== undefined) {
                ammo[weapon.id] = weapon.max_ammo;
            }
        });

        // 開始から現在ターンまでのログを走査して状態を再現
        for (const log of logs) {
            if (log.turn > currentTurn) break;

            // 位置更新
            if (log.actor_id === targetId && log.position_snapshot) {
                pos = log.position_snapshot;
            }

            // HP更新 (DAMAGEログは actor_id = ダメージを受けた側 になっている前提のロジックなら)
            // ※ Simulation.pyの実装を確認すると、DAMAGEログのactor_idは「攻撃された側」にしていましたね。
            if (log.action_type === "DAMAGE" && log.actor_id === targetId && log.damage) {
                hp -= log.damage;
            }
            // もしATTACKログの命中時にHPを減らす実装ならそちらを見る必要がありますが、
            // 今回のsimulation.pyではATTACKログの中にdamageを入れています。
            // ATTACKログの場合: actor=攻撃者, target=被害者
            if (log.action_type === "ATTACK" && log.target_id === targetId && log.damage) {
                hp -= log.damage;
            }
            
            // リソース消費の推測（簡易版）
            // 注意: この実装では最初の武器を常に使用すると仮定しています
            // ログデータに武器情報が含まれていないため、実際の武器使用を追跡できません
            if (log.action_type === "ATTACK" && log.actor_id === targetId) {
                const weapon = initialMs.weapons[0]; // 簡略化: 最初の武器を使用と仮定
                if (weapon) {
                    if (weapon.en_cost) {
                        en = Math.max(0, en - weapon.en_cost);
                    }
                    if (weapon.max_ammo && ammo[weapon.id] !== undefined) {
                        ammo[weapon.id] = Math.max(0, ammo[weapon.id] - 1);
                    }
                }
            }
        }

        return { pos, hp: Math.max(0, hp), en, ammo };
    };

    // 環境に応じた背景色を決定
    const getEnvironmentColor = () => {
        switch (environment) {
            case "GROUND":
                return "#1a3a1a"; // 濃い緑
            case "COLONY":
                return "#2a2a3a"; // 濃い紫
            case "UNDERWATER":
                return "#0a2a3a"; // 濃い青
            case "SPACE":
            default:
                return "#000000"; // 黒
        }
    };

    const playerState = getSnapshot(player.id, player);
    const enemyStates = enemies.map(enemy => ({
        enemy,
        state: getSnapshot(enemy.id, enemy)
    }));

    return (
        <div className="w-full h-[400px] rounded border border-green-800 mb-4 overflow-hidden relative" style={{ backgroundColor: getEnvironmentColor() }}>
            <Canvas
                camera={{ position: [50, 50, 50], fov: 60 }}
                dpr={[1, 2]}
            >
                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} intensity={1.5} />

                <Stars radius={100} depth={50} count={2000} factor={4} fade speed={1} />
                <Grid 
                    infiniteGrid 
                    sectionSize={10} 
                    cellSize={1} 
                    fadeDistance={100} 
                    sectionColor={environment === "COLONY" ? "#6a6a9a" : "#00ff00"} 
                    cellColor={environment === "COLONY" ? "#3a3a5a" : "#003300"} 
                />
                <OrbitControls />

                {/* Environment Effects */}
                <EnvironmentEffects environment={environment} />

                {/* Player */}
                <MobileSuitMesh
                    position={playerState.pos}
                    maxHp={player.max_hp}
                    currentHp={playerState.hp}
                    name={player.name}
                    sensorRange={player.sensor_range}
                    showSensorRange={true}
                />

                {/* Enemies */}
                {enemyStates.map(({ enemy, state }) => (
                    <MobileSuitMesh
                        key={enemy.id}
                        position={state.pos}
                        maxHp={enemy.max_hp}
                        currentHp={state.hp}
                        name={enemy.name}
                        sensorRange={enemy.sensor_range}
                        showSensorRange={false}
                    />
                ))}
            </Canvas>

            {/* UIオーバーレイ */}
            <div className="absolute top-2 left-2 text-white bg-black/60 p-2 text-xs font-mono pointer-events-none rounded border border-green-900/50">
                <div className="mb-2 border-b border-blue-500/30 pb-2">
                    <span className="font-bold text-blue-400">{player.name}</span>
                    <br />
                    HP: {playerState.hp} / {player.max_hp}
                    <div className="w-24 h-1 bg-gray-700 mt-1">
                        <div className="h-full bg-blue-500 transition-all duration-300" style={{ width: `${(playerState.hp / player.max_hp) * 100}%` }}></div>
                    </div>
                    
                    {/* EN Display */}
                    <div className="mt-1">
                        <span className="text-cyan-400">EN:</span> {playerState.en} / {player.max_en || DEFAULT_MAX_EN}
                        <div className="w-24 h-1 bg-gray-700 mt-1">
                            <div className="h-full bg-cyan-500 transition-all duration-300" style={{ width: `${(playerState.en / (player.max_en || DEFAULT_MAX_EN)) * 100}%` }}></div>
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
                        <div className="w-24 h-1 bg-gray-700 mt-1">
                            <div className="h-full bg-red-500 transition-all duration-300" style={{ width: `${(state.hp / enemy.max_hp) * 100}%` }}></div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Environment Label */}
            <div className="absolute top-2 right-2 text-white bg-black/60 px-3 py-1 text-xs font-mono pointer-events-none rounded border border-green-900/50">
                <span className="text-green-400">環境:</span> {environment}
            </div>
        </div>
    );
}