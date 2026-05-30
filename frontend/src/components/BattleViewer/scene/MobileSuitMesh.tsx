/* frontend/src/components/BattleViewer/scene/MobileSuitMesh.tsx */

"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
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
    name,
    sensorRange,
    showSensorRange,
    warnings,
    heading,
    isTargeted,
    isAttacking,
    isFlashing,
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
    /** 現在攻撃中の場合 true — 射撃反動アニメーション用 (Issue #365) */
    isAttacking?: boolean;
    /** クリティカルヒット被弾時 true — emissiveIntensity フラッシュ用 (Issue #367) */
    isFlashing?: boolean;
}) {
    const scale = 0.05;
    const vec = new THREE.Vector3(position.x * scale, position.z * scale, position.y * scale);
    const color = getHpColor(currentHp, maxHp);

    // ホバリングアニメーション用グループ ref (B-4)
    const hoverGroupRef = useRef<THREE.Group>(null);
    // MS名称から固定シードを生成（各機がバラバラのタイミングで揺れる）
    const seedOffset = useMemo(
        () => Array.from(name).reduce((acc, c) => acc + c.charCodeAt(0), 0),
        [name],
    );

    // 射撃反動アニメーション用内側グループ ref と経過タイマー (Issue #365)
    const innerGroupRef = useRef<THREE.Group>(null);
    const recoilTimeRef = useRef(0);
    const RECOIL_DURATION = 0.25; // 反動アニメーション持続時間（秒）

    // クリティカルフラッシュ用球体 ref と経過タイマー (B-5)
    const sphereMeshRef = useRef<THREE.Mesh>(null);
    const flashTimeRef = useRef(0);
    const FLASH_DURATION = 0.4;

    useFrame((state, delta) => {
        // B-4: ホバリングアニメーション（宇宙浮遊感）
        if (hoverGroupRef.current) {
            const hpRatio = maxHp > 0 ? currentHp / maxHp : 1;
            // HP 20% 以下: 振幅・周波数を大きくして被弾感を演出
            const amplitude = hpRatio <= 0.2 ? 0.08 : 0.05;
            const frequency = hpRatio <= 0.2 ? 1.2 : 0.8;
            hoverGroupRef.current.position.y =
                Math.sin(state.clock.elapsedTime * frequency + seedOffset) * amplitude;
        }

        if (!innerGroupRef.current) return;

        // 射撃反動アニメーション (Issue #365)
        if (isAttacking) {
            recoilTimeRef.current = RECOIL_DURATION;
        }
        if (recoilTimeRef.current > 0) {
            recoilTimeRef.current = Math.max(0, recoilTimeRef.current - delta);
            const t = 1 - recoilTimeRef.current / RECOIL_DURATION; // 0 → 1
            // 減衰振動: sin波 × 線形減衰
            const recoil = Math.sin(t * Math.PI * 5) * 0.12 * (1 - t);
            innerGroupRef.current.position.x = recoil;
        } else {
            innerGroupRef.current.position.x = 0;
        }

        // B-5: クリティカルフラッシュ（emissiveIntensity を瞬間的に上げて減衰）
        if (isFlashing) flashTimeRef.current = FLASH_DURATION;
        if (sphereMeshRef.current) {
            const baseIntensity = isTargeted ? 1.2 : 0.3;
            if (flashTimeRef.current > 0) {
                flashTimeRef.current = Math.max(0, flashTimeRef.current - delta);
                const decay = flashTimeRef.current / FLASH_DURATION; // 1 → 0
                (sphereMeshRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity =
                    baseIntensity + 3.0 * decay;
            } else {
                (sphereMeshRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity =
                    baseIntensity;
            }
        }
    });

    // 向き矢印（ArrowHelper）の生成
    const headingArrow = useMemo(() => {
        if (heading === undefined) return null;
        const headingRad = (heading * Math.PI) / 180;
        // ゲーム座標→Three.js座標: game.x→X, game.z→Y, game.y(高さ=0)→Z
        // バックエンド: direction=[cos,0,sin] (XZ平面) → Three.js: (cos, sin, 0) (XY平面)
        const dir = new THREE.Vector3(
            Math.cos(headingRad), Math.sin(headingRad), 0
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
            {/* B-4: ホバリングアニメーション用グループ (Issue #367) */}
            <group ref={hoverGroupRef}>
            {/* 射撃反動アニメーション用内側グループ (Issue #365) */}
            <group ref={innerGroupRef}>
                <mesh ref={sphereMeshRef} scale={[2, 2, 2]}>
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
            </group>
        </group>
    );
}
