/* frontend/src/components/BattleViewer.tsx */
"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
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

// MSを表示する球体コンポーネント
function MobileSuitMesh({
    position,
    maxHp,
    currentHp,
    name
}: {
    position: { x: number; y: number; z: number };
    maxHp: number;
    currentHp: number;
    name: string;
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
        </group>
    );
}

interface BattleViewerProps {
    logs: BattleLog[];
    ms1: MobileSuit;
    ms2: MobileSuit;
    currentTurn: number;
}

export default function BattleViewer({ logs, ms1, ms2, currentTurn }: BattleViewerProps) {

    // 現在のターン時点での情報を計算する関数
    const getSnapshot = (targetId: string, initialMs: MobileSuit) => {
        let pos = initialMs.position;
        let hp = initialMs.max_hp; // 戦闘開始時は満タンと仮定（あるいはinitialMs.current_hp）

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
        }

        return { pos, hp: Math.max(0, hp) };
    };

    const state1 = getSnapshot(ms1.id, ms1);
    const state2 = getSnapshot(ms2.id, ms2);

    return (
        <div className="w-full h-[400px] bg-black rounded border border-green-800 mb-4 overflow-hidden relative">
            <Canvas
                camera={{ position: [50, 50, 50], fov: 60 }}
                dpr={[1, 2]}
            >
                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} intensity={1.5} />

                <Stars radius={100} depth={50} count={2000} factor={4} fade speed={1} />
                <Grid infiniteGrid sectionSize={10} cellSize={1} fadeDistance={100} sectionColor={"#00ff00"} cellColor={"#003300"} />
                <OrbitControls />

                {/* MS 1 */}
                <MobileSuitMesh
                    position={state1.pos}
                    maxHp={ms1.max_hp}
                    currentHp={state1.hp}
                    name={ms1.name}
                />

                {/* MS 2 */}
                <MobileSuitMesh
                    position={state2.pos}
                    maxHp={ms2.max_hp}
                    currentHp={state2.hp}
                    name={ms2.name}
                />
            </Canvas>

            {/* UIオーバーレイ */}
            <div className="absolute top-2 left-2 text-white bg-black/60 p-2 text-xs font-mono pointer-events-none rounded border border-green-900/50">
                <div className="mb-2">
                    <span className="font-bold text-blue-400">{ms1.name}</span>
                    <br />
                    HP: {state1.hp} / {ms1.max_hp}
                    <div className="w-24 h-1 bg-gray-700 mt-1">
                        <div className="h-full bg-blue-500 transition-all duration-300" style={{ width: `${(state1.hp / ms1.max_hp) * 100}%` }}></div>
                    </div>
                </div>
                <div>
                    <span className="font-bold text-red-400">{ms2.name}</span>
                    <br />
                    HP: {state2.hp} / {ms2.max_hp}
                    <div className="w-24 h-1 bg-gray-700 mt-1">
                        <div className="h-full bg-red-500 transition-all duration-300" style={{ width: `${(state2.hp / ms2.max_hp) * 100}%` }}></div>
                    </div>
                </div>
            </div>
        </div>
    );
}