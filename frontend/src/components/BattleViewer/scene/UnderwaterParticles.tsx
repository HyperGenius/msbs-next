/* frontend/src/components/BattleViewer/scene/UnderwaterParticles.tsx */

"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

// 水中浮遊パーティクルコンポーネント
export function UnderwaterParticles() {
    const particlesRef = useRef<THREE.Points>(null);
    
    // パーティクルの位置を生成（メモ化して一度だけ計算）
    const positions = useMemo(() => {
        const particleCount = 200;
        const pos = new Float32Array(particleCount * 3);
        for (let i = 0; i < particleCount; i++) {
            // eslint-disable-next-line react-hooks/purity
            pos[i * 3] = (Math.random() - 0.5) * 100;
            // eslint-disable-next-line react-hooks/purity
            pos[i * 3 + 1] = (Math.random() - 0.5) * 40;
            // eslint-disable-next-line react-hooks/purity
            pos[i * 3 + 2] = (Math.random() - 0.5) * 100;
        }
        return pos;
    }, []); // 空の依存配列で初回のみ計算
    
    const particleCount = positions.length / 3;
    
    useFrame((state) => {
        if (particlesRef.current) {
            // ゆっくりと上昇する動き
            particlesRef.current.position.y = (state.clock.elapsedTime * 0.5) % 20 - 10;
            particlesRef.current.rotation.y = state.clock.elapsedTime * 0.1;
        }
    });
    
    return (
        <points ref={particlesRef}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={particleCount}
                    array={positions}
                    itemSize={3}
                    args={[positions, 3]}
                />
            </bufferGeometry>
            <pointsMaterial
                size={0.1}
                color="#5ac5ea"
                transparent
                opacity={0.3}
                sizeAttenuation
            />
        </points>
    );
}
