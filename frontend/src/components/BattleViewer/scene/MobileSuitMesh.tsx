/* frontend/src/components/BattleViewer/scene/MobileSuitMesh.tsx */

"use client";

import { useMemo } from "react";
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
    prevHp,
    sensorRange,
    showSensorRange,
    warnings,
    heading,
    isTargeted,
}: {
    position: { x: number; y: number; z: number };
    maxHp: number;
    currentHp: number;
    prevHp?: number;
    name: string;
    sensorRange?: number;
    showSensorRange?: boolean;
    warnings?: WarningType[];
    /** 自機の向き（度数法）— 向き矢印表示に使用（自機のみ） */
    heading?: number;
    /** ターゲットされている場合 true — ハイライトリング表示に使用 */
    isTargeted?: boolean;
}) {
    const scale = 0.05;
    const vec = new THREE.Vector3(position.x * scale, position.z * scale, position.y * scale);
    const color = getHpColor(currentHp, maxHp);

    // 向き矢印（ArrowHelper）の生成
    const headingArrow = useMemo(() => {
        if (heading === undefined) return null;
        const headingRad = (heading * Math.PI) / 180;
        const dir = new THREE.Vector3(
            Math.sin(headingRad), 0, Math.cos(headingRad)
        ).normalize();
        return new THREE.ArrowHelper(dir, new THREE.Vector3(0, 0, 0), 4, 0x4488ff, 1.5, 1.0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [heading]);

    // 撃破されたターンのみ💥を表示（前のターンでHPが残っていた場合のみ）
    if (currentHp <= 0) {
        const wasJustDestroyed = prevHp === undefined || prevHp > 0;
        if (!wasJustDestroyed) return null;
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
                    emissiveIntensity={isTargeted ? 1.2 : 0.3}
                />
            </mesh>

            {/* ターゲットハイライトリング */}
            {isTargeted && (
                <mesh rotation={[-Math.PI / 2, 0, 0]}>
                    <ringGeometry args={[1.4, 1.8, 32]} />
                    <meshBasicMaterial color={0xff4444} side={THREE.DoubleSide} transparent opacity={0.85} />
                </mesh>
            )}
            
            {/* Sensor Range Visualization - Enhanced with animation */}
            {showSensorRange && sensorRange && (
                <AnimatedSensorRing sensorRange={sensorRange} scale={scale} />
            )}

            {/* 向き矢印（自機のみ: heading が指定された場合のみ表示） */}
            {headingArrow && <primitive object={headingArrow} />}
            
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
