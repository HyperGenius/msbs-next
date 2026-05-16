/* frontend/src/components/BattleViewer/scene/ObstacleMesh.tsx */

"use client";

import { Obstacle } from "@/types/battle";

const OBSTACLE_SCALE = 0.05;

interface ObstacleMeshProps {
    obstacle: Obstacle;
    environment?: string;
}

export function ObstacleMesh({ obstacle, environment = "SPACE" }: ObstacleMeshProps) {
    const x = obstacle.position.x * OBSTACLE_SCALE;
    const y = obstacle.position.z * OBSTACLE_SCALE;
    const z = obstacle.position.y * OBSTACLE_SCALE;
    const r = obstacle.radius * OBSTACLE_SCALE;
    const h = Math.max(obstacle.height * OBSTACLE_SCALE, r * 2);

    const color = environment === "GROUND" ? "#4a5a4a" : "#5a4a3a";

    return (
        <mesh position={[x, y + h / 2, z]}>
            <cylinderGeometry args={[r, r, h, 16]} />
            <meshStandardMaterial
                color={color}
                roughness={0.9}
                metalness={0.1}
                transparent
                opacity={0.75}
            />
        </mesh>
    );
}
