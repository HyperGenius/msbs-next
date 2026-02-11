/* frontend/src/components/BattleViewer/scene/BattleScene.tsx */

"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars, Grid } from "@react-three/drei";
import { MobileSuit } from "@/types/battle";
import { EnvironmentEffects } from "./EnvironmentEffects";
import { MobileSuitMesh } from "./MobileSuitMesh";
import { BattleEventDisplay } from "./BattleEventDisplay";
import { BattleEventEffect, WarningType } from "../types";

interface UnitState {
    pos: { x: number; y: number; z: number };
    hp: number;
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
}

export function BattleScene({
    environment,
    player,
    playerState,
    playerEvent,
    enemyStates,
    enemyEvents,
}: BattleSceneProps) {
    return (
        <Canvas
            camera={{ position: [50, 50, 50], fov: 60 }}
            dpr={[1, 2]}
        >
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
                return event && enemyData ? (
                    <BattleEventDisplay key={id} position={enemyData.state.pos} event={event} />
                ) : null;
            })}
        </Canvas>
    );
}
