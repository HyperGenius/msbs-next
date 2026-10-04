/* frontend/src/components/BattleViewer/scene/EnvironmentEffects.tsx */

"use client";

import * as THREE from "three";
import { UnderwaterParticles } from "./UnderwaterParticles";
import { FOREST_FLOOR_Y, getEnvironmentColor } from "../utils";

interface EnvironmentEffectsProps {
    environment: string;
    /** フィールド中心のシーン座標。FOREST の林床をフィールドに合わせて敷くために使う。 */
    fieldCenter?: number;
    /** フィールドの一辺の長さ（シーン単位）。 */
    fieldSpan?: number;
}

// 環境エフェクトコンポーネント
export function EnvironmentEffects({ environment, fieldCenter = 0, fieldSpan = 200 }: EnvironmentEffectsProps) {
    const getFogColor = () => {
        switch (environment) {
            case "GROUND":
                return "#2a5a2a"; // 緑系の霧
            case "FOREST":
                return getEnvironmentColor("FOREST"); // 背景と同色にして地平線を馴染ませる
            case "COLONY":
                return "#4a4a6a"; // 紫系の霧
            case "UNDERWATER":
                return "#1a4a6a"; // 青系の霧
            case "SPACE":
            default:
                return "#000000"; // 霧なし
        }
    };
    
    const fogColor = getFogColor();
    
    switch (environment) {
        case "GROUND":
            return (
                <>
                    {/* 明るい照明 */}
                    <directionalLight position={[10, 20, 10]} intensity={1.2} />
                    <hemisphereLight args={['#87CEEB', '#2a3a2a', 0.6]} />
                    <fog attach="fog" args={[fogColor, 30, 120]} />
                    {/* 地面の表現 */}
                    <mesh position={[0, -2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshStandardMaterial color="#3a5a3a" roughness={0.9} />
                    </mesh>
                    {/* 空の表現 (簡易版) */}
                    <mesh position={[0, 50, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshBasicMaterial color="#87CEEB" side={THREE.BackSide} />
                    </mesh>
                </>
            );
        case "FOREST":
            return (
                <>
                    {/* 樹冠越しの柔らかい光 */}
                    <directionalLight position={[15, 25, 5]} intensity={0.9} color="#e8f0d0" />
                    <hemisphereLight args={['#b8d8a8', '#1a2a1a', 0.5]} />
                    <fog attach="fog" args={[fogColor, 35, 140]} />
                    {/* 林床 */}
                    <mesh position={[fieldCenter, FOREST_FLOOR_Y, fieldCenter]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[fieldSpan * 2, fieldSpan * 2]} />
                        <meshStandardMaterial color="#2b3f24" roughness={1} />
                    </mesh>
                </>
            );
        case "COLONY":
            return (
                <>
                    {/* 人工的な照明 */}
                    <ambientLight intensity={0.4} />
                    <pointLight position={[0, 20, 0]} intensity={1.0} color="#ffffff" />
                    <fog attach="fog" args={[fogColor, 30, 120]} />
                    {/* 強調されたメタリック床 */}
                    <mesh position={[0, -2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshStandardMaterial 
                            color="#3a3a5a" 
                            roughness={0.3}
                            metalness={0.7}
                        />
                    </mesh>
                    {/* 人工的な天井/空 */}
                    <mesh position={[0, 40, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshBasicMaterial color="#5a5a7a" side={THREE.BackSide} />
                    </mesh>
                </>
            );
        case "UNDERWATER":
            return (
                <>
                    {/* 暗めで青い照明 */}
                    <ambientLight intensity={0.3} color="#1a4a6a" />
                    <directionalLight position={[0, 10, 0]} intensity={0.5} color="#3a8aba" />
                    <fog attach="fog" args={[fogColor, 15, 80]} />
                    {/* 水面エフェクト（簡易版） */}
                    <mesh position={[0, 15, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[200, 200]} />
                        <meshStandardMaterial 
                            color="#1a4a6a" 
                            transparent 
                            opacity={0.4} 
                            roughness={0.1}
                            metalness={0.8}
                        />
                    </mesh>
                    {/* 浮遊パーティクル */}
                    <UnderwaterParticles />
                </>
            );
        case "SPACE":
        default:
            return (
                <>
                    {/* 暗い照明 */}
                    <ambientLight intensity={0.3} />
                </>
            );
    }
}
