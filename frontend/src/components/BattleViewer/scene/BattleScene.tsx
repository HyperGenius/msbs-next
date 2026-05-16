/* frontend/src/components/BattleViewer/scene/BattleScene.tsx */

"use client";

import { useRef, useEffect, useMemo } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Stars, Grid } from "@react-three/drei";
import * as THREE from "three";
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
    /** 現在の胴体向き（度数法）— 自機のみ向き矢印に使用 */
    heading?: number;
    /** 現在のターゲットMS ID — 照準線・ハイライトに使用 */
    targetId?: string;
}

/** LOS 計算結果（1本の視線ライン分） */
interface LosResult {
    enemyId: string;
    clear: boolean;
    blockedBy: string | null;
    playerPos: { x: number; y: number; z: number };
    enemyPos: { x: number; y: number; z: number };
}

interface BattleSceneProps {
    environment: string;
    player: MobileSuit;
    playerState: UnitState;
    playerEvent: BattleEventEffect | null;
    enemyStates: Array<{ enemy: MobileSuit; state: UnitState }>;
    enemyEvents: Array<{ id: string; event: BattleEventEffect | null }>;
    obstacles?: Obstacle[];
    /** LOS 表示が ON のときのみ渡される計算済み LOS 結果 */
    losResults?: LosResult[];
}

/** 自機からターゲット敵MSへの照準線コンポーネント */
function TargetLine({
    playerPos,
    targetPos,
}: {
    playerPos: { x: number; y: number; z: number };
    targetPos: { x: number; y: number; z: number };
}) {
    const lineObject = useMemo(() => {
        const p1 = new THREE.Vector3(
            playerPos.x * POSITION_SCALE,
            playerPos.z * POSITION_SCALE,
            playerPos.y * POSITION_SCALE,
        );
        const p2 = new THREE.Vector3(
            targetPos.x * POSITION_SCALE,
            targetPos.z * POSITION_SCALE,
            targetPos.y * POSITION_SCALE,
        );
        const geometry = new THREE.BufferGeometry().setFromPoints([p1, p2]);
        const material = new THREE.LineDashedMaterial({
            color: 0xff4444,
            dashSize: 1,
            gapSize: 0.5,
            linewidth: 1,
        });
        const line = new THREE.Line(geometry, material);
        line.computeLineDistances();
        return line;
    }, [
        playerPos.x, playerPos.y, playerPos.z,
        targetPos.x, targetPos.y, targetPos.z,
    ]);

    return <primitive object={lineObject} />;
}

/** 攻撃ラインコンポーネント（命中: 黄色実線 / ミス: グレー破線） */
function AttackLine({
    fromPos,
    toPos,
    hit,
}: {
    fromPos: { x: number; y: number; z: number };
    toPos: { x: number; y: number; z: number };
    hit: boolean;
}) {
    const lineObject = useMemo(() => {
        const p1 = new THREE.Vector3(
            fromPos.x * POSITION_SCALE,
            fromPos.z * POSITION_SCALE,
            fromPos.y * POSITION_SCALE,
        );
        const p2 = new THREE.Vector3(
            toPos.x * POSITION_SCALE,
            toPos.z * POSITION_SCALE,
            toPos.y * POSITION_SCALE,
        );
        const geometry = new THREE.BufferGeometry().setFromPoints([p1, p2]);
        let material: THREE.LineBasicMaterial | THREE.LineDashedMaterial;
        if (hit) {
            // 命中: 黄色実線（太め）
            material = new THREE.LineBasicMaterial({
                color: 0xffcc00,
                linewidth: 2,
            });
        } else {
            // ミス: グレー破線（細め）
            material = new THREE.LineDashedMaterial({
                color: 0x888888,
                dashSize: 1,
                gapSize: 0.5,
                linewidth: 1,
            });
        }
        const line = new THREE.Line(geometry, material);
        if (!hit) line.computeLineDistances();
        return line;
    }, [
        fromPos.x, fromPos.y, fromPos.z,
        toPos.x, toPos.y, toPos.z,
        hit,
    ]);

    return <primitive object={lineObject} />;
}


function LosLine({
    playerPos,
    enemyPos,
    clear,
}: {
    playerPos: { x: number; y: number; z: number };
    enemyPos: { x: number; y: number; z: number };
    clear: boolean;
}) {
    const lineObject = useMemo(() => {
        const p1 = new THREE.Vector3(
            playerPos.x * POSITION_SCALE,
            playerPos.z * POSITION_SCALE,
            playerPos.y * POSITION_SCALE,
        );
        const p2 = new THREE.Vector3(
            enemyPos.x * POSITION_SCALE,
            enemyPos.z * POSITION_SCALE,
            enemyPos.y * POSITION_SCALE,
        );
        const geometry = new THREE.BufferGeometry().setFromPoints([p1, p2]);
        const material = new THREE.LineDashedMaterial({
            color: clear ? 0x00ff88 : 0xff4444,
            dashSize: clear ? 3 : 0.8,
            gapSize: clear ? 1.5 : 0.4,
            linewidth: 1,
            transparent: true,
            opacity: clear ? 0.5 : 0.85,
        });
        const line = new THREE.Line(geometry, material);
        line.computeLineDistances();
        return line;
    }, [
        playerPos.x, playerPos.y, playerPos.z,
        enemyPos.x, enemyPos.y, enemyPos.z,
        clear,
    ]);

    return <primitive object={lineObject} />;
}


export function BattleScene({
    environment,
    player,
    playerState,
    playerEvent,
    enemyStates,
    enemyEvents,
    obstacles,
    losResults,
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

    // 自機のターゲット敵MSの状態（照準線・ハイライト用）
    const targetedEnemy = playerState.targetId
        ? enemyStates.find(({ enemy }) => enemy.id === playerState.targetId)
        : undefined;

    // LOS によって遮断されている障害物 ID のセット
    const blockingObstacleIds = useMemo(() => {
        if (!losResults) return new Set<string>();
        return new Set<string>(
            losResults
                .filter(r => !r.clear && r.blockedBy !== null)
                .map(r => r.blockedBy as string)
        );
    }, [losResults]);

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
                heading={playerState.heading}
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
                    isTargeted={enemy.id === playerState.targetId}
                />
            ))}

            {/* 自機 → ターゲット敵MSへの照準線 */}
            {targetedEnemy && targetedEnemy.state.hp > 0 && (
                <TargetLine
                    playerPos={playerState.pos}
                    targetPos={targetedEnemy.state.pos}
                />
            )}
            
            {/* Battle Event Effects */}
            {playerEvent && (
                <BattleEventDisplay position={playerState.pos} event={playerEvent} />
            )}
            {playerEvent?.targetPos && (
                <AttackLine
                    fromPos={playerState.pos}
                    toPos={playerEvent.targetPos}
                    hit={playerEvent.hit ?? true}
                />
            )}
            {enemyEvents.map(({ id, event }) => {
                const enemyData = enemyStates.find(e => e.enemy.id === id);
                if (!event || !enemyData || enemyData.state.hp <= 0) return null;
                return (
                    <group key={id}>
                        <BattleEventDisplay position={enemyData.state.pos} event={event} />
                        {event.targetPos && (
                            <AttackLine
                                fromPos={enemyData.state.pos}
                                toPos={event.targetPos}
                                hit={event.hit ?? true}
                            />
                        )}
                    </group>
                );
            })}

            {/* LOS 視線ライン（showLos が ON のときのみ表示） */}
            {losResults && losResults.map((result) => (
                <LosLine
                    key={result.enemyId}
                    playerPos={result.playerPos}
                    enemyPos={result.enemyPos}
                    clear={result.clear}
                />
            ))}

            {/* Obstacles */}
            {obstacles && obstacles.map((obs) => (
                <ObstacleMesh
                    key={obs.obstacle_id}
                    obstacle={obs}
                    environment={environment}
                    isBlocking={blockingObstacleIds.has(obs.obstacle_id)}
                />
            ))}
        </Canvas>
    );
}
