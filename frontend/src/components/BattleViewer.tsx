/* frontend/src/components/BattleViewer.tsx */
"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars, Grid, Html } from "@react-three/drei";
import { BattleLog, MobileSuit } from "@/types/battle";
import * as THREE from "three";

// 色計算用のヘルパー
function getHpColor(current: number, max: number) {
    const ratio = current / max;
    if (ratio > 0.5) return "green"; // 余裕
    if (ratio > 0.2) return "yellow"; // 注意
    return "red"; // 危険
}

// HPバーの色を計算
function getHpBarColor(ratio: number): string {
    if (ratio > 0.5) return '#3b82f6'; // 青
    if (ratio > 0.2) return '#eab308'; // 黄
    return '#ef4444'; // 赤
}

// 敵のHPバーの色を計算
function getEnemyHpBarColor(ratio: number): string {
    if (ratio > 0.5) return '#ef4444'; // 赤
    if (ratio > 0.2) return '#eab308'; // 黄
    return '#dc2626'; // 濃い赤
}

// デフォルト値定数
const DEFAULT_MAX_EN = 1000;
const EN_WARNING_THRESHOLD = 0.2; // 20%以下でEN不足警告
const RESIST_PATTERN = /(\d+)%軽減/; // 軽減率パターン

// 警告アイコンの種類
type WarningType = 'ammo' | 'energy' | 'cooldown';

// バトルイベント効果の種類
interface BattleEventEffect {
    type: 'critical' | 'resist' | 'guard' | 'damage';
    text: string;
    color: string;
}

// バトルイベントを表示するコンポーネント
function BattleEventDisplay({ 
    position, 
    event 
}: { 
    position: { x: number; y: number; z: number }; 
    event: BattleEventEffect | null;
}) {
    const scale = 0.05;
    const vec = new THREE.Vector3(position.x * scale, position.z * scale, position.y * scale);
    
    if (!event) return null;
    
    return (
        <Html position={[vec.x, vec.y + 5, vec.z]} center>
            <div 
                className="animate-bounce pointer-events-none font-bold text-center"
                style={{
                    color: event.color,
                    textShadow: `0 0 10px ${event.color}, 0 0 20px ${event.color}`,
                    fontSize: event.type === 'critical' ? '20px' : '16px',
                    fontWeight: 'bold',
                }}
            >
                {event.text}
            </div>
        </Html>
    );
}

// MSを表示する球体コンポーネント
function MobileSuitMesh({
    position,
    maxHp,
    currentHp,
    sensorRange,
    showSensorRange,
    name,
    warnings,
}: {
    position: { x: number; y: number; z: number };
    maxHp: number;
    currentHp: number;
    name: string;
    sensorRange?: number;
    showSensorRange?: boolean;
    warnings?: WarningType[];
}) {
    const scale = 0.05;
    const vec = new THREE.Vector3(position.x * scale, position.z * scale, position.y * scale);
    const color = getHpColor(currentHp, maxHp);

    // 警告アイコンのマッピング
    const warningIcons: Record<WarningType, { icon: string; color: string; label: string }> = {
        ammo: { icon: '⚠️', color: '#ff9800', label: '弾切れ' },
        energy: { icon: '⚡', color: '#ffeb3b', label: 'EN不足' },
        cooldown: { icon: '⏳', color: '#2196f3', label: 'クールダウン' }
    };

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
            
            {/* Sensor Range Visualization - Enhanced with grid pattern */}
            {showSensorRange && sensorRange && (
                <>
                    {/* Main sensor ring with grid effect */}
                    <mesh position={[0, -1.8, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <ringGeometry args={[sensorRange * scale * 0.95, sensorRange * scale, 64]} />
                        <meshBasicMaterial color="#00ff00" transparent opacity={0.3} side={THREE.DoubleSide} />
                    </mesh>
                    {/* Inner pulsing circle for better visibility */}
                    <mesh position={[0, -1.75, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <circleGeometry args={[sensorRange * scale, 32]} />
                        <meshBasicMaterial color="#00ff00" transparent opacity={0.05} side={THREE.DoubleSide} />
                    </mesh>
                </>
            )}
            
            {/* Status Warning Indicators above the unit */}
            {warnings && warnings.length > 0 && (
                <Html position={[0, 3, 0]} center>
                    <div className="flex gap-1 items-center pointer-events-none">
                        {warnings.map((warning, idx) => {
                            const info = warningIcons[warning];
                            return (
                                <div 
                                    key={idx}
                                    className="flex flex-col items-center text-xs font-bold px-2 py-1 rounded"
                                    style={{ 
                                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                        border: `2px solid ${info.color}`,
                                        color: info.color
                                    }}
                                >
                                    <span className="text-lg">{info.icon}</span>
                                    <span className="text-[10px] whitespace-nowrap">{info.label}</span>
                                </div>
                            );
                        })}
                    </div>
                </Html>
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
                    {/* 明るい照明 */}
                    <directionalLight position={[10, 20, 10]} intensity={1.2} />
                    <hemisphereLight args={['#87CEEB', '#2a3a2a', 0.6]} />
                    <fog attach="fog" args={[fogColor, 30, 120]} />
                    {/* 地面の表現 */}
                    <mesh position={[0, -2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshStandardMaterial color="#3a5a3a" roughness={0.9} />
                    </mesh>
                    {/* 空の表現 (簡易版) */}
                    <mesh position={[0, 50, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshBasicMaterial color="#87CEEB" side={THREE.BackSide} />
                    </mesh>
                </>
            );
        case "COLONY":
            return (
                <>
                    {/* 人工的な照明 */}
                    <ambientLight intensity={0.4} />
                    <pointLight position={[0, 20, 0]} intensity={1.0} color="#ffffff" />
                    <fog attach="fog" args={[fogColor, 30, 120]} />
                    {/* 人工的な天井/空 */}
                    <mesh position={[0, 40, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshBasicMaterial color="#5a5a7a" side={THREE.BackSide} />
                    </mesh>
                </>
            );
        case "UNDERWATER":
            return (
                <>
                    {/* 暗めで青い照明 */}
                    <ambientLight intensity={0.3} color="#1a4a6a" />
                    <directionalLight position={[0, 10, 0]} intensity={0.5} color="#3a8aba" />
                    <fog attach="fog" args={[fogColor, 15, 80]} />
                    {/* 水面エフェクト（簡易版） */}
                    <mesh position={[0, 15, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshStandardMaterial 
                            color="#1a4a6a" 
                            transparent 
                            opacity={0.4} 
                            roughness={0.1}
                            metalness={0.8}
                        />
                    </mesh>
                </>
            );
        case "SPACE":
        default:
            return (
                <>
                    {/* 暗い照明 */}
                    <ambientLight intensity={0.3} />
                </>
            );
    }
}

export default function BattleViewer({ logs, player, enemies, currentTurn, environment = "SPACE" }: BattleViewerProps) {

    // 現在のターン時点での情報を計算する関数
    const getSnapshot = (targetId: string, initialMs: MobileSuit) => {
        let pos = initialMs.position;
        let hp = initialMs.max_hp; // 戦闘開始時は満タンと仮定（あるいはinitialMs.current_hp）
        let en = initialMs.max_en || DEFAULT_MAX_EN;
        const ammo: Record<string, number> = {};
        const warnings: WarningType[] = [];
        
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
        
        // 警告状態を判定
        // EN不足: EN_WARNING_THRESHOLD以下
        const maxEn = initialMs.max_en || DEFAULT_MAX_EN;
        if (maxEn > 0 && en / maxEn < EN_WARNING_THRESHOLD) {
            warnings.push('energy');
        }
        
        // 弾切れ: 第1武器の弾薬が0
        const firstWeapon = initialMs.weapons[0];
        if (firstWeapon && firstWeapon.max_ammo !== null && firstWeapon.max_ammo !== undefined) {
            if (ammo[firstWeapon.id] === 0) {
                warnings.push('ammo');
            }
        }
        
        // クールダウン判定（簡易版：最後の攻撃から一定ターン以内）
        // 注: より正確な実装には武器ごとのクールダウン追跡が必要
        let lastAttackTurn = 0;
        for (let i = logs.length - 1; i >= 0; i--) {
            if (logs[i].action_type === "ATTACK" && logs[i].actor_id === targetId) {
                lastAttackTurn = logs[i].turn;
                break;
            }
        }
        const cooldownTurns = firstWeapon?.cool_down_turn || 0;
        if (cooldownTurns > 0 && currentTurn - lastAttackTurn < cooldownTurns) {
            warnings.push('cooldown');
        }

        return { pos, hp: Math.max(0, hp), en, ammo, warnings };
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
    
    // 現在のターンのログを一度だけフィルタリング
    const currentTurnLogs = logs.filter(log => log.turn === currentTurn);
    
    // ユニットIDごとのバトルイベントマップを作成（パフォーマンス最適化）
    const battleEventMap = new Map<string, BattleEventEffect | null>();
    
    for (const log of currentTurnLogs) {
        // クリティカルヒット検出
        if (log.action_type === "ATTACK" && log.actor_id && 
            log.message.includes("クリティカルヒット") && !battleEventMap.has(log.actor_id)) {
            battleEventMap.set(log.actor_id, {
                type: 'critical',
                text: 'CRITICAL HIT!!',
                color: '#ff0000'
            });
        }
        
        // 防御/軽減検出（ダメージを受けた側）
        if (log.action_type === "ATTACK" && log.target_id && !battleEventMap.has(log.target_id)) {
            if (log.message.includes("対ビーム装甲により") || log.message.includes("対実弾装甲により")) {
                const resistMatch = log.message.match(RESIST_PATTERN);
                const percent = resistMatch ? resistMatch[1] : '';
                battleEventMap.set(log.target_id, {
                    type: 'resist',
                    text: `RESIST ${percent}%`,
                    color: '#4caf50'
                });
            } else if (log.damage && log.damage > 0) {
                // 通常ダメージの場合、ダメージ数値を表示
                battleEventMap.set(log.target_id, {
                    type: 'damage',
                    text: `-${log.damage}`,
                    color: '#ff5722'
                });
            }
        }
    }
    
    const playerEvent = battleEventMap.get(player.id) || null;
    const enemyEvents = enemies.map(enemy => ({
        id: enemy.id,
        event: battleEventMap.get(enemy.id) || null
    }));

    return (
        <div className="w-full h-[400px] rounded border border-green-800 mb-4 overflow-hidden relative" style={{ backgroundColor: getEnvironmentColor() }}>
            <Canvas
                camera={{ position: [50, 50, 50], fov: 60 }}
                dpr={[1, 2]}
            >
                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} intensity={1.5} />

                {/* Only show stars in SPACE environment */}
                {environment === "SPACE" && (
                    <Stars radius={100} depth={50} count={2000} factor={4} fade speed={1} />
                )}
                <Grid 
                    infiniteGrid 
                    sectionSize={10} 
                    cellSize={1} 
                    fadeDistance={100} 
                    sectionColor={environment === "COLONY" ? "#8a8aaa" : "#00ff00"} 
                    cellColor={environment === "COLONY" ? "#4a4a6a" : "#003300"} 
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
                    warnings={playerState.warnings}
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
                        warnings={state.warnings}
                    />
                ))}
                
                {/* Battle Event Effects */}
                {playerEvent && (
                    <BattleEventDisplay position={playerState.pos} event={playerEvent} />
                )}
                {enemyEvents.map(({ id, event }) => {
                    const enemyData = enemyStates.find(e => e.enemy.id === id);
                    return event && enemyData ? (
                        <BattleEventDisplay key={id} position={enemyData.state.pos} event={event} />
                    ) : null;
                })}
            </Canvas>

            {/* UIオーバーレイ */}
            <div className="absolute top-2 left-2 text-white bg-black/60 p-2 text-xs font-mono pointer-events-none rounded border border-green-900/50">
                <div className="mb-2 border-b border-blue-500/30 pb-2">
                    <span className="font-bold text-blue-400">{player.name}</span>
                    <br />
                    HP: {playerState.hp} / {player.max_hp}
                    <div className="w-24 h-2 bg-gray-700 mt-1 rounded overflow-hidden border border-gray-600">
                        <div 
                            className="h-full transition-all duration-300" 
                            style={{ 
                                width: `${(playerState.hp / player.max_hp) * 100}%`,
                                backgroundColor: getHpBarColor(playerState.hp / player.max_hp)
                            }}
                        ></div>
                    </div>
                    
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
                        <div className="w-24 h-2 bg-gray-700 mt-1 rounded overflow-hidden border border-gray-600">
                            <div 
                                className="h-full transition-all duration-300" 
                                style={{ 
                                    width: `${(state.hp / enemy.max_hp) * 100}%`,
                                    backgroundColor: getEnemyHpBarColor(state.hp / enemy.max_hp)
                                }}
                            ></div>
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