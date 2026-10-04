/* frontend/src/components/BattleViewer/scene/ForestGroves.tsx */

"use client";

import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { Obstacle } from "@/types/battle";
import { FOREST_FLOOR_Y } from "../utils";
import { layoutGrove, TreePlacement } from "../utils/forestLayout";

const OBSTACLE_SCALE = 0.05;
const TRUNK_HEIGHT_RATIO = 0.35;
const CANOPY_BASE_RATIO = 0.25;
// 要素数は FOREST_CANOPY_SHADES と揃える
const CANOPY_COLORS: readonly string[] = ["#2f5a2c", "#3d6b34", "#284d2a"];
const TRUNK_COLOR = "#4a3626";
// LOS 遮断時の色は ObstacleMesh の強調表示と同じ値にする
const BLOCKING_COLOR = "#8a3a3a";
const BLOCKING_EDGE_COLOR = "#ff4444";
// 林床との Z ファイティングを避ける高さ。センサー範囲リングよりは下にする。
const FOOTPRINT_OFFSET_Y = 0.1;
// グリッド（y=0）は深度を書き込む。その下にある接地影は、グリッドより先に描かないと隠れる。
const FOOTPRINT_RENDER_ORDER = -1;

interface ForestGrovesProps {
    obstacles: Obstacle[];
    blockingObstacleIds: Set<string>;
}

type InstanceTransform = (tree: TreePlacement, position: THREE.Vector3, scale: THREE.Vector3) => void;

/** 林床から木の頂点までの高さ。頂点の高さは障害物の座標から決める。 */
function heightAboveFloor(tree: TreePlacement): number {
    return tree.y + tree.height - FOREST_FLOOR_Y;
}

const trunkTransform: InstanceTransform = (tree, position, scale) => {
    const trunkHeight = heightAboveFloor(tree) * TRUNK_HEIGHT_RATIO;
    const trunkRadius = tree.canopyRadius * 0.18;
    position.set(tree.x, FOREST_FLOOR_Y + trunkHeight / 2, tree.z);
    scale.set(trunkRadius, trunkHeight, trunkRadius);
};

const canopyTransform: InstanceTransform = (tree, position, scale) => {
    const totalHeight = heightAboveFloor(tree);
    const canopyHeight = totalHeight * (1 - CANOPY_BASE_RATIO);
    position.set(tree.x, FOREST_FLOOR_Y + totalHeight * CANOPY_BASE_RATIO + canopyHeight / 2, tree.z);
    scale.set(tree.canopyRadius, canopyHeight, tree.canopyRadius);
};

/** 全木立の木を 1 つの InstancedMesh に書き込む。 */
function useTreeInstances(
    trees: TreePlacement[],
    transform: InstanceTransform,
    colorOf: (tree: TreePlacement) => string,
) {
    const ref = useRef<THREE.InstancedMesh>(null);
    useLayoutEffect(() => {
        const mesh = ref.current;
        if (!mesh) return;
        const matrix = new THREE.Matrix4();
        const position = new THREE.Vector3();
        const scale = new THREE.Vector3();
        const rotation = new THREE.Quaternion();
        const color = new THREE.Color();
        trees.forEach((tree, i) => {
            transform(tree, position, scale);
            mesh.setMatrixAt(i, matrix.compose(position, rotation, scale));
            mesh.setColorAt(i, color.set(colorOf(tree)));
        });
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
        // 視錐台カリングは全インスタンスを含む境界球で判定するため、行列を変えたら作り直す
        mesh.computeBoundingSphere();
    }, [trees, transform, colorOf]);
    return ref;
}

/**
 * 森林の障害物を木立として描く。
 * 木の数が多いため、幹と樹冠をそれぞれ 1 回の描画呼び出しにまとめる。
 */
export function ForestGroves({ obstacles, blockingObstacleIds }: ForestGrovesProps) {
    const trees = useMemo(
        () => obstacles.flatMap((obstacle) => layoutGrove(obstacle, OBSTACLE_SCALE)),
        [obstacles],
    );

    const trunkColorOf = useMemo(
        () => (tree: TreePlacement) => (blockingObstacleIds.has(tree.obstacleId) ? BLOCKING_COLOR : TRUNK_COLOR),
        [blockingObstacleIds],
    );
    const canopyColorOf = useMemo(
        () => (tree: TreePlacement) =>
            blockingObstacleIds.has(tree.obstacleId) ? BLOCKING_COLOR : CANOPY_COLORS[tree.shade],
        [blockingObstacleIds],
    );
    const trunkRef = useTreeInstances(trees, trunkTransform, trunkColorOf);
    const canopyRef = useTreeInstances(trees, canopyTransform, canopyColorOf);

    if (trees.length === 0) return null;

    return (
        <group>
            {/* InstancedMesh の最大数は生成時に決まる。木の数が変わったら作り直す。 */}
            <instancedMesh key={`trunk-${trees.length}`} ref={trunkRef} args={[undefined, undefined, trees.length]}>
                <cylinderGeometry args={[0.7, 1, 1, 5]} />
                <meshStandardMaterial roughness={1} />
            </instancedMesh>
            <instancedMesh key={`canopy-${trees.length}`} ref={canopyRef} args={[undefined, undefined, trees.length]}>
                <coneGeometry args={[1, 1, 7]} />
                <meshStandardMaterial roughness={0.95} flatShading transparent opacity={0.85} />
            </instancedMesh>
            {obstacles.map((obstacle) => {
                const x = obstacle.position.x * OBSTACLE_SCALE;
                const z = obstacle.position.z * OBSTACLE_SCALE;
                const r = obstacle.radius * OBSTACLE_SCALE;
                const isBlocking = blockingObstacleIds.has(obstacle.obstacle_id);
                return (
                    <group key={obstacle.obstacle_id} position={[x, FOREST_FLOOR_Y + FOOTPRINT_OFFSET_Y, z]} rotation={[-Math.PI / 2, 0, 0]}>
                        {/* 接地影: 木立の範囲（LOS 判定の半径）を示す */}
                        <mesh renderOrder={FOOTPRINT_RENDER_ORDER}>
                            <circleGeometry args={[r * 1.05, 20]} />
                            <meshBasicMaterial color="#000000" transparent opacity={0.3} depthWrite={false} />
                        </mesh>
                        {isBlocking && (
                            <mesh position={[0, 0, 0.02]} renderOrder={FOOTPRINT_RENDER_ORDER}>
                                <ringGeometry args={[r * 0.95, r * 1.05, 32]} />
                                <meshBasicMaterial color={BLOCKING_EDGE_COLOR} transparent opacity={0.9} depthWrite={false} />
                            </mesh>
                        )}
                    </group>
                );
            })}
        </group>
    );
}
