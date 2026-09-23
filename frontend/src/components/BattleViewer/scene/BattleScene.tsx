/* frontend/src/components/BattleViewer/scene/BattleScene.tsx */

"use client";

import { useRef, useEffect, useMemo, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Stars, Grid } from "@react-three/drei";
import * as THREE from "three";
import { MobileSuit } from "@/types/battle";
import { EnvironmentEffects } from "./EnvironmentEffects";
import { MobileSuitMesh } from "./MobileSuitMesh";
import { ObstacleMesh } from "./ObstacleMesh";
import { TracerMesh } from "./TracerMesh";
import { WeaponLabel } from "./WeaponLabel";
import { ImpactMarker } from "./ImpactMarker";
import { AttackEvent, WarningType } from "../types";
import { useAttackEffectQueue } from "../hooks/useAttackEffectQueue";
import { Obstacle } from "@/types/battle";
import { getEnvironmentColor } from "../utils";

// MobileSuitMesh と同じスケール定数（座標変換の一貫性）
const POSITION_SCALE = 0.05;

// map_bounds が未取得（旧バトル履歴等）の場合のフォールバック値。
// backend/app/engine/constants.py の MAP_BOUNDS デフォルトと合わせる
const DEFAULT_MAP_BOUNDS: [number, number] = [0, 5000];

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

// チャプタージャンプ時のみカメラターゲットを自機位置へ再センタリングするコンポーネント（Issue #524）。
// CameraInitializer と異なり camera.position（距離・角度）は変更せず target のみ更新することで、
// ユーザーが直前まで操作していたズーム・回転を保持する
function CameraRecenterer({
    px, py, pz,
    recenterToken,
    controlsRef,
}: {
    px: number;
    py: number;
    pz: number;
    recenterToken?: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    controlsRef: React.RefObject<any>;
}) {
    useEffect(() => {
        // recenterToken は 0 始まりのため、マウント時（実際のチャプタークリック前）に
        // 誤って再センタリングされないよう 0 以下は無視する
        if (!recenterToken || recenterToken <= 0) return;

        let cancelled = false;
        let frameId: number;

        // controlsRef（OrbitControls）がまだ生成されていないタイミングでこの effect が
        // 実行された場合に備え、生成されるまで次フレームでリトライする
        const applyRecenter = () => {
            if (cancelled) return;
            if (controlsRef.current) {
                controlsRef.current.target.set(px, py, pz);
                controlsRef.current.update();
            } else {
                frameId = requestAnimationFrame(applyRecenter);
            }
        };
        applyRecenter();

        return () => {
            cancelled = true;
            if (frameId) cancelAnimationFrame(frameId);
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [recenterToken]);

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
    enemyStates: Array<{ enemy: MobileSuit; state: UnitState }>;
    /** 現在タイムスタンプの攻撃。射線・武器名・着弾演出をスポーンする。 */
    attacks: AttackEvent[];
    /** 現在タイムスタンプでクリティカルを受けたユニット ID セット（機体フラッシュ用） */
    criticalTargetIds: Set<string>;
    obstacles?: Obstacle[];
    /** フィールド範囲 [min, max] (m)。背景グリッドをフィールドに整列させるために使用 (Issue #436) */
    mapBounds?: [number, number] | null;
    /** LOS 表示が ON のときのみ渡される計算済み LOS 結果 */
    losResults?: LosResult[];
    /** 現在タイムスタンプで攻撃アクション中のユニット ID セット（射撃反動アニメーション用）*/
    attackingUnitIds?: Set<string>;
    /** 現在の再生タイムスタンプ（攻撃演出のスポーン検出用） */
    currentTimestamp: number;
    /** チャプタージャンプ時のみ増分されるトークン。カメラターゲットの再センタリングをトリガーする（Issue #524） */
    recenterToken?: number;
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
            playerPos.y * POSITION_SCALE,
            playerPos.z * POSITION_SCALE,
        );
        const p2 = new THREE.Vector3(
            targetPos.x * POSITION_SCALE,
            targetPos.y * POSITION_SCALE,
            targetPos.z * POSITION_SCALE,
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
            playerPos.y * POSITION_SCALE,
            playerPos.z * POSITION_SCALE,
        );
        const p2 = new THREE.Vector3(
            enemyPos.x * POSITION_SCALE,
            enemyPos.y * POSITION_SCALE,
            enemyPos.z * POSITION_SCALE,
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
    enemyStates,
    attacks,
    criticalTargetIds,
    obstacles,
    mapBounds,
    losResults,
    attackingUnitIds,
    currentTimestamp,
    recenterToken,
}: BattleSceneProps) {
    // フィールド中心・全体をカバーするグリッドの位置とフェード距離を算出（Issue #436）
    const [mapMin, mapMax] = mapBounds ?? DEFAULT_MAP_BOUNDS;
    const fieldCenter = ((mapMin + mapMax) / 2) * POSITION_SCALE;
    const fieldSpan = (mapMax - mapMin) * POSITION_SCALE;
    const gridFadeDistance = Math.max(100, fieldSpan * 1.2);
    // 自機MS初期Three.js座標をマウント時のみキャプチャ（MobileSuitMesh と同じ軸変換）
    const [initialPos] = useState(() => ({
        x: playerState.pos.x * POSITION_SCALE,
        y: playerState.pos.y * POSITION_SCALE, // game.y（高度、通常0）→ Three.js の高さ方向 y
        z: playerState.pos.z * POSITION_SCALE, // game.z（地面平面の第2軸）→ Three.js の奥行き方向 z
    }));
    const { x: px, y: py, z: pz } = initialPos;
    // チャプタージャンプ時の再センタリング先。毎レンダーで現在の自機位置から再計算する（初期化専用の initialPos とは別物）
    const currentPos = {
        x: playerState.pos.x * POSITION_SCALE,
        y: playerState.pos.y * POSITION_SCALE,
        z: playerState.pos.z * POSITION_SCALE,
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const controlsRef = useRef<any>(null);

    // 射線の始点・終点と演出の表示位置。未索敵の敵は含まない
    const unitPositions = useMemo(() => {
        const map = new Map<string, { x: number; y: number; z: number }>();
        map.set(String(player.id), playerState.pos);
        enemyStates.forEach(({ enemy, state }) => map.set(String(enemy.id), state.pos));
        return map;
    }, [player.id, playerState.pos, enemyStates]);

    const { tracers, labels, impacts, removeTracer, removeLabel, removeImpact } = useAttackEffectQueue({
        attacks,
        positions: unitPositions,
        playerId: String(player.id),
        currentTimestamp,
    });

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

            {/* チャプタージャンプ時のみカメラターゲットを自機の新しい位置へ再センタリング（Issue #524） */}
            <CameraRecenterer
                px={currentPos.x}
                py={currentPos.y}
                pz={currentPos.z}
                recenterToken={recenterToken}
                controlsRef={controlsRef}
            />

            {/* 距離フォグ: 背景色(getEnvironmentColor)と同色にして遠景を自然に馴染ませ、奥行き感を出す */}
            <fog attach="fog" args={[getEnvironmentColor(environment), 90, 220]} />

            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1.5} />

            {/* Only show stars in SPACE environment */}
            {environment === "SPACE" && (
                <Stars radius={100} depth={50} count={2000} factor={4} fade speed={1} />
            )}
            <Grid
                position={[fieldCenter, 0, fieldCenter]}
                infiniteGrid
                sectionSize={10}
                cellSize={1}
                fadeDistance={gridFadeDistance}
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
                isAttacking={attackingUnitIds?.has(String(player.id))}
                isFlashing={criticalTargetIds.has(String(player.id))}
                isSelf={true}
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
                    isAttacking={attackingUnitIds?.has(String(enemy.id))}
                    isFlashing={criticalTargetIds.has(String(enemy.id))}
                />
            ))}

            {/* 自機 → ターゲット敵MSへの照準線（自機・ターゲット双方が生存している場合のみ表示） */}
            {playerState.hp > 0 && targetedEnemy && targetedEnemy.state.hp > 0 && (
                <TargetLine
                    playerPos={playerState.pos}
                    targetPos={targetedEnemy.state.pos}
                />
            )}

            {/* 攻撃演出: 射線 → 発射側の武器名 → 着弾フラッシュと数字 */}
            {tracers.map(t => (
                <TracerMesh
                    key={t.id}
                    from={t.from}
                    to={t.to}
                    kind={t.kind}
                    color={t.color}
                    startAt={t.startAt}
                    durationMs={t.durationMs}
                    onComplete={() => removeTracer(t.id)}
                />
            ))}
            {labels.map(l => (
                <WeaponLabel key={l.id} label={l} onComplete={() => removeLabel(l.id)} />
            ))}
            {impacts.map(i => (
                <ImpactMarker key={i.id} impact={i} onComplete={() => removeImpact(i.id)} />
            ))}

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
