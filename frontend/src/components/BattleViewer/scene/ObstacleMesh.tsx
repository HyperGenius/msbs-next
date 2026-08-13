/* frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx */

"use client";

import { Edges } from "@react-three/drei";
import { Obstacle } from "@/types/battle";

const OBSTACLE_SCALE = 0.05;

interface ObstacleMeshProps {
    obstacle: Obstacle;
    environment?: string;
    /** true のとき、LOS を遮断している障害物として赤みがかった色で強調表示する */
    isBlocking?: boolean;
}

export function ObstacleMesh({ obstacle, environment = "SPACE", isBlocking = false }: ObstacleMeshProps) {
    const x = obstacle.position.x * OBSTACLE_SCALE;
    const y = obstacle.position.z * OBSTACLE_SCALE;
    const z = obstacle.position.y * OBSTACLE_SCALE;
    const r = obstacle.radius * OBSTACLE_SCALE;
    const h = Math.max(obstacle.height * OBSTACLE_SCALE, r * 2);

    const normalColor = environment === "GROUND" ? "#4a5a4a" : "#5a4a3a";
    const color = isBlocking ? "#8a3a3a" : normalColor;
    // 輪郭線: 塗りと同じ色相を明るくした色を使用（isBlocking は既存パレットの赤 #ff4444 を流用）
    const normalEdgeColor = environment === "GROUND" ? "#8fb88f" : "#b89b78";
    const edgeColor = isBlocking ? "#ff4444" : normalEdgeColor;

    return (
        <group>
            {/* 接地影: 暗い背景でも障害物の設置位置・奥行きが分かるようにする */}
            <mesh position={[x, y + 0.02, z]} rotation={[-Math.PI / 2, 0, 0]}>
                <circleGeometry args={[r * 1.15, 24]} />
                <meshBasicMaterial color="#000000" transparent opacity={0.35} depthWrite={false} />
            </mesh>
            <mesh position={[x, y + h / 2, z]}>
                <cylinderGeometry args={[r, r, h, 16]} />
                <meshStandardMaterial
                    color={color}
                    roughness={0.9}
                    metalness={0.1}
                    transparent
                    opacity={isBlocking ? 0.9 : 0.75}
                />
                <Edges color={edgeColor} threshold={15} />
            </mesh>
        </group>
    );
}
