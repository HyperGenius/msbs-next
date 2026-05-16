/* frontend/src/components/BattleViewer/scene/BattleScene.tsx */

"use client";

import { useRef, useEffect } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Stars, Grid } from "@react-three/drei";
import { MobileSuit } from "@/types/battle";
import { EnvironmentEffects } from "./EnvironmentEffects";
import { MobileSuitMesh } from "./MobileSuitMesh";
import { BattleEventDisplay } from "./BattleEventDisplay";
import { ObstacleMesh } from "./ObstacleMesh";
import { BattleEventEffect, WarningType } from "../types";
import { Obstacle } from "@/types/battle";

// MobileSuitMesh と同じスケール定数（座標変換の一貫性）
const POSITION_SCALE = 0.05;

// モーダルオープン時に自機MSを中心にカメラを初期配置するコンポーネント
// Canvas 内部で useThree を呼ぶため、Canvas の子として定義する必要がある
function CameraInitializer({
    px, py, pz,
    controlsRef,
}: {
    px: number;
    py: number;
    pz: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    controlsRef: React.RefObject<any>;
}) {
    const { camera } = useThree();

    useEffect(() => {
        // 自機MS初期位置を中心にカメラを配置（マウント時のみ実行）
        camera.position.set(px + 50, py + 50, pz + 50);
        if (controlsRef.current) {
            controlsRef.current.target.set(px, py, pz);
            controlsRef.current.update();
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return null;
}

interface UnitState {
    pos: { x: number; y: number; z: number };
    hp: number;
    prevHp: number;
    en: number;
    ammo: Record<string, number>;
    warnings: WarningType[];
}

interface BattleSceneProps {
    environment: string;
    player: MobileSuit;
    playerState: UnitState;
    playerEvent: BattleEventEffect | null;
    enemyStates: Array<{ enemy: MobileSuit; state: UnitState }>;
    enemyEvents: Array<{ id: string; event: BattleEventEffect | null }>;
    obstacles?: Obstacle[];
}

export function BattleScene({
    environment,
    player,
    playerState,
    playerEvent,
    enemyStates,
    enemyEvents,
    obstacles,
}: BattleSceneProps) {
    // 自機MS初期Three.js座標をマウント時のみキャプチャ（MobileSuitMesh と同じ軸変換）
    const initialPos = useRef({
        x: playerState.pos.x * POSITION_SCALE,
        y: playerState.pos.z * POSITION_SCALE, // game.z → Three.js の高さ方向 y
        z: playerState.pos.y * POSITION_SCALE, // game.y → Three.js の奥行き方向 z
    });
    const { x: px, y: py, z: pz } = initialPos.current;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const controlsRef = useRef<any>(null);

    return (
        <Canvas
            camera={{ position: [50, 50, 50], fov: 60 }}
            dpr={[1, 2]}
        >
            {/* モーダルオープン時に自機MSを中心にカメラを初期配置 */}
            <CameraInitializer px={px} py={py} pz={pz} controlsRef={controlsRef} />

            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1.5} />

            {/* Only show stars in SPACE environment */}
            {environment === "SPACE" && (
                <Stars radius={100} depth={50} count={2000} factor={4} fade speed={1} />
            )}
            <Grid 
                infiniteGrid 
                sectionSize={10} 
                cellSize={1} 
                fadeDistance={100} 
                sectionColor={environment === "COLONY" ? "#8a8aaa" : "#00ff00"} 
                cellColor={environment === "COLONY" ? "#4a4a6a" : "#003300"} 
            />
            <OrbitControls
                ref={controlsRef}
                enableZoom={true}
                enablePan={true}
                enableRotate={true}
                zoomSpeed={0.5}
                rotateSpeed={0.5}
                panSpeed={0.5}
                minDistance={30}
                maxDistance={150}
                enableDamping={true}
                dampingFactor={0.05}
                touches={{
                    ONE: 2, // TOUCH.ROTATE - One finger to rotate
                    TWO: 1  // TOUCH.DOLLY_PAN - Two fingers to zoom/pan
                }}
            />

            {/* Environment Effects */}
            <EnvironmentEffects environment={environment} />

            {/* Player */}
            <MobileSuitMesh
                position={playerState.pos}
                maxHp={player.max_hp}
                currentHp={playerState.hp}
                prevHp={playerState.prevHp}
                name={player.name}
                sensorRange={player.sensor_range}
                showSensorRange={true}
                warnings={playerState.warnings}
            />

            {/* Enemies */}
            {enemyStates.map(({ enemy, state }) => (
                <MobileSuitMesh
                    key={enemy.id}
                    position={state.pos}
                    maxHp={enemy.max_hp}
                    currentHp={state.hp}
                    prevHp={state.prevHp}
                    name={enemy.name}
                    sensorRange={enemy.sensor_range}
                    showSensorRange={false}
                    warnings={state.warnings}
                />
            ))}
            
            {/* Battle Event Effects */}
            {playerEvent && (
                <BattleEventDisplay position={playerState.pos} event={playerEvent} />
            )}
            {enemyEvents.map(({ id, event }) => {
                const enemyData = enemyStates.find(e => e.enemy.id === id);
                if (!event || !enemyData || enemyData.state.hp <= 0) return null;
                return (
                    <BattleEventDisplay key={id} position={enemyData.state.pos} event={event} />
                );
            })}

            {/* Obstacles */}
            {obstacles && obstacles.map((obs) => (
                <ObstacleMesh key={obs.obstacle_id} obstacle={obs} environment={environment} />
            ))}
        </Canvas>
    );
}
