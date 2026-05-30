/* frontend/src/components/BattleViewer/scene/ProjectileMesh.tsx */

"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const POSITION_SCALE = 0.05;

/** ビーム武器かどうかを判定するヘルパー（weapon_name の文字列で区別） */
export function isBeamWeapon(weaponName?: string): boolean {
    if (!weaponName) return false;
    const lower = weaponName.toLowerCase();
    return lower.includes("beam") || weaponName.includes("ビーム") || lower.includes("mega particle");
}

interface ProjectileMeshProps {
    fromPos: { x: number; y: number; z: number };
    toPos: { x: number; y: number; z: number };
    weaponType: "BEAM" | "BULLET";
    /** スポーン時刻（Date.now()） */
    startTime: number;
    /** 飛翔アニメーション時間（ms） */
    duration: number;
    onComplete: () => void;
}

/** 飛翔体エフェクト（B-3）: 射手→目標座標へ lerp でアニメーション */
export function ProjectileMesh({
    fromPos,
    toPos,
    weaponType,
    startTime,
    duration,
    onComplete,
}: ProjectileMeshProps) {
    const meshRef = useRef<THREE.Mesh>(null);
    const completedRef = useRef(false);

    // ゲーム座標 → Three.js 座標変換（BattleScene の軸変換と統一: x→X, z→Y, y→Z）
    const from3D = new THREE.Vector3(
        fromPos.x * POSITION_SCALE,
        fromPos.z * POSITION_SCALE,
        fromPos.y * POSITION_SCALE,
    );
    const to3D = new THREE.Vector3(
        toPos.x * POSITION_SCALE,
        toPos.z * POSITION_SCALE,
        toPos.y * POSITION_SCALE,
    );

    useFrame(() => {
        if (completedRef.current || !meshRef.current) return;

        const elapsed = Date.now() - startTime;
        const t = Math.min(elapsed / duration, 1);

        // lerp で位置を更新
        const pos = new THREE.Vector3().lerpVectors(from3D, to3D, t);
        meshRef.current.position.copy(pos);

        // ビームは末端でフェードアウト
        if (weaponType === "BEAM" && meshRef.current.material) {
            const mat = meshRef.current.material as THREE.MeshBasicMaterial;
            mat.opacity = t > 0.75 ? (1 - t) / 0.25 : 1;
        }

        if (t >= 1 && !completedRef.current) {
            completedRef.current = true;
            onComplete();
        }
    });

    if (weaponType === "BEAM") {
        return (
            <mesh ref={meshRef} position={from3D}>
                <sphereGeometry args={[0.15, 8, 8]} />
                <meshBasicMaterial
                    color="#aaff44"
                    transparent
                    opacity={1}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
        );
    }

    return (
        <mesh ref={meshRef} position={from3D}>
            <sphereGeometry args={[0.2, 8, 8]} />
            <meshBasicMaterial color="#aaaaaa" />
        </mesh>
    );
}
