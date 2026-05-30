/* frontend/src/components/BattleViewer/scene/HitEffectMesh.tsx */

"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const POSITION_SCALE = 0.05;

/** エフェクト種別ごとの設定 */
const EFFECT_CONFIG = {
    hit: { count: 8, color: "#ffcc00", duration: 300, spread: 2.5, opacity: 1.0, hasCriticalFlash: false },
    critical: { count: 12, color: "#ff4400", duration: 500, spread: 4.0, opacity: 1.0, hasCriticalFlash: true },
    miss: { count: 6, color: "#888888", duration: 250, spread: 2.0, opacity: 0.5, hasCriticalFlash: false },
} as const;

interface HitEffectMeshProps {
    position: { x: number; y: number; z: number };
    effectType: "hit" | "critical" | "miss";
    /** スポーン開始時刻（Date.now()） */
    startTime: number;
    onComplete: () => void;
}

/** 3Dヒットエフェクト（B-5）: 命中位置にスプライトパーティクルを展開 */
export function HitEffectMesh({
    position,
    effectType,
    startTime,
    onComplete,
}: HitEffectMeshProps) {
    const groupRef = useRef<THREE.Group>(null);
    const flashRef = useRef<THREE.Mesh>(null);
    const completedRef = useRef(false);
    const config = EFFECT_CONFIG[effectType];

    // ゲーム座標 → Three.js 座標変換
    const center3D = new THREE.Vector3(
        position.x * POSITION_SCALE,
        position.z * POSITION_SCALE,
        position.y * POSITION_SCALE,
    );

    // 各パーティクルの初期方向ベクトルを事前計算（球面上にランダム分布）
    const directions = useMemo(() => {
        const dirs: THREE.Vector3[] = [];
        for (let i = 0; i < config.count; i++) {
            // 均等分布: フィボナッチ球面サンプリング
            const phi = Math.acos(1 - 2 * (i + 0.5) / config.count);
            const theta = Math.PI * (1 + Math.sqrt(5)) * i;
            dirs.push(new THREE.Vector3(
                Math.sin(phi) * Math.cos(theta),
                Math.cos(phi),
                Math.sin(phi) * Math.sin(theta),
            ).normalize());
        }
        return dirs;
    }, [config.count]);

    useFrame(() => {
        if (completedRef.current) return;

        const elapsed = Date.now() - startTime;
        // 開始前は非表示
        if (elapsed < 0) {
            if (groupRef.current) groupRef.current.visible = false;
            return;
        }

        const t = Math.min(elapsed / config.duration, 1);

        if (groupRef.current) {
            groupRef.current.visible = true;
            // 各パーティクルを外側へ展開しながらフェードアウト
            groupRef.current.children.forEach((child, i) => {
                if (i >= config.count) return; // 閃光メッシュは別処理
                const dir = directions[i];
                if (!dir) return;
                const mesh = child as THREE.Mesh;
                mesh.position.copy(dir).multiplyScalar(t * config.spread);
                const mat = mesh.material as THREE.MeshBasicMaterial;
                mat.opacity = config.opacity * (1 - t);
            });
        }

        // クリティカル閃光メッシュ（t が小さいうちだけ表示）
        if (flashRef.current && config.hasCriticalFlash) {
            const mat = flashRef.current.material as THREE.MeshBasicMaterial;
            mat.opacity = t < 0.3 ? config.opacity * (1 - t / 0.3) : 0;
            // 徐々に拡大
            const flashScale = 1 + t * 3;
            flashRef.current.scale.set(flashScale, flashScale, 1);
        }

        if (t >= 1 && !completedRef.current) {
            completedRef.current = true;
            onComplete();
        }
    });

    return (
        <group position={center3D}>
            {/* クリティカル閃光: カメラ向きの大型プレーン */}
            {config.hasCriticalFlash && (
                <mesh ref={flashRef}>
                    <planeGeometry args={[2, 2]} />
                    <meshBasicMaterial
                        color={config.color}
                        transparent
                        opacity={1}
                        blending={THREE.AdditiveBlending}
                        depthWrite={false}
                        side={THREE.DoubleSide}
                    />
                </mesh>
            )}
            {/* パーティクル群 */}
            <group ref={groupRef}>
                {directions.map((_, i) => (
                    <mesh key={i}>
                        <sphereGeometry args={[effectType === "critical" ? 0.2 : 0.12, 4, 4]} />
                        <meshBasicMaterial
                            color={config.color}
                            transparent
                            opacity={config.opacity}
                            blending={THREE.AdditiveBlending}
                            depthWrite={false}
                        />
                    </mesh>
                ))}
            </group>
        </group>
    );
}
