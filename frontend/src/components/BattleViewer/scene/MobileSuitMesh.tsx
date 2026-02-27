/* frontend/src/components/BattleViewer/scene/MobileSuitMesh.tsx */

"use client";

import { Html } from "@react-three/drei";
import * as THREE from "three";
import { getHpColor } from "../utils";
import { WarningType } from "../types";
import { AnimatedSensorRing } from "./AnimatedSensorRing";

// MSを表示する球体コンポーネント
export function MobileSuitMesh({
    position,
    maxHp,
    currentHp,
    sensorRange,
    showSensorRange,
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

    if (currentHp <= 0) {
        return (
            <group position={vec}>
                <Html center>
                    <div
                        className="animate-pulse pointer-events-none select-none text-4xl"
                        style={{ filter: "drop-shadow(0 0 8px #ff4400) drop-shadow(0 0 16px #ff8800)" }}
                    >
                        💥
                    </div>
                </Html>
            </group>
        );
    }

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
                <meshStandardMaterial
                    color={color}
                    roughness={0.5}
                    metalness={0.1}
                    emissive={color}
                    emissiveIntensity={0.3}
                />
            </mesh>
            
            {/* Sensor Range Visualization - Enhanced with animation */}
            {showSensorRange && sensorRange && (
                <AnimatedSensorRing sensorRange={sensorRange} scale={scale} />
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
