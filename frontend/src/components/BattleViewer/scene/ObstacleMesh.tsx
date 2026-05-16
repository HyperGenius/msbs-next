/* frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx */

"use client";

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

    return (
        <mesh position={[x, y + h / 2, z]}>
            <cylinderGeometry args={[r, r, h, 16]} />
            <meshStandardMaterial
                color={color}
                roughness={0.9}
                metalness={0.1}
                transparent
                opacity={isBlocking ? 0.9 : 0.75}
            />
        </mesh>
    );
}
