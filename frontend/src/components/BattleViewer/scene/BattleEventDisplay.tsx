/* frontend/src/components/BattleViewer/scene/BattleEventDisplay.tsx */

"use client";

import { Html } from "@react-three/drei";
import * as THREE from "three";
import { BattleEventEffect } from "../types";

// バトルイベントを表示するコンポーネント
export function BattleEventDisplay({ 
    position, 
    event 
}: { 
    position: { x: number; y: number; z: number }; 
    event: BattleEventEffect | null;
}) {
    const scale = 0.05;
    const vec = new THREE.Vector3(position.x * scale, position.z * scale, position.y * scale);
    
    if (!event) return null;
    
    return (
        <Html position={[vec.x, vec.y + 5, vec.z]} center>
            <div 
                className="animate-bounce pointer-events-none font-bold text-center"
                style={{
                    color: event.color,
                    textShadow: `0 0 10px ${event.color}, 0 0 20px ${event.color}`,
                    fontSize: event.type === 'critical' ? '20px' : '16px',
                    fontWeight: 'bold',
                }}
            >
                {event.text}
            </div>
        </Html>
    );
}
