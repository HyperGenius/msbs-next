/* frontend/src/components/BattleViewer/scene/AnimatedSensorRing.tsx */

"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

// アニメーション付きセンサーリングコンポーネント
export function AnimatedSensorRing({ sensorRange, scale }: { sensorRange: number; scale: number }) {
    const ringRef = useRef<THREE.Mesh>(null);
    const circleRef = useRef<THREE.Mesh>(null);
    
    useFrame((state) => {
        if (ringRef.current && circleRef.current) {
            // パルス効果: 0.3 から 0.5 の間で透明度を変化
            const opacity = 0.3 + Math.sin(state.clock.elapsedTime * 2) * 0.2;
            (ringRef.current.material as THREE.MeshBasicMaterial).opacity = opacity;
            (circleRef.current.material as THREE.MeshBasicMaterial).opacity = opacity * 0.15;
        }
    });
    
    return (
        <>
            {/* メインセンサーリング */}
            <mesh ref={ringRef} position={[0, -1.8, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <ringGeometry args={[sensorRange * scale * 0.95, sensorRange * scale, 64]} />
                <meshBasicMaterial color="#00ff00" transparent opacity={0.3} side={THREE.DoubleSide} />
            </mesh>
            {/* 内側の円 */}
            <mesh ref={circleRef} position={[0, -1.75, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <circleGeometry args={[sensorRange * scale, 32]} />
                <meshBasicMaterial color="#00ff00" transparent opacity={0.05} side={THREE.DoubleSide} />
            </mesh>
        </>
    );
}
