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
    // attack_line 型はテキスト表示なし（Three.js ラインのみ描画）
    if (event.type === 'attack_line') return null;
    
    const isCritical = event.type === 'critical';
    const fontSize = isCritical ? '20px' : '16px';

    return (
        <Html position={[vec.x, vec.y + 5, vec.z]} center>
            <div className="pointer-events-none text-center">
                {event.weaponName && (
                    <div
                        style={{
                            fontSize: '11px',
                            color: '#cccccc',
                            textShadow: '0 0 4px #000000',
                            marginBottom: '2px',
                            fontWeight: 'bold',
                        }}
                    >
                        {event.weaponName}
                    </div>
                )}
                <div
                    className="animate-bounce font-bold"
                    style={{
                        color: event.color,
                        textShadow: `0 0 10px ${event.color}, 0 0 20px ${event.color}`,
                        fontSize,
                        fontWeight: 'bold',
                    }}
                >
                    {event.text}
                </div>
            </div>
        </Html>
    );
}
