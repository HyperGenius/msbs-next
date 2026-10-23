/* frontend/src/components/BattleViewer/scene/RetreatPointMarker.tsx */

"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { RetreatPointView } from "@/types/battle";
import { HIT_EFFECT_COLORS } from "../utils";

const POSITION_SCALE = 0.05;
const SEGMENTS = 64;
// 地面にめり込まないよう、わずかに浮かせる
const GROUND_LIFT = 0.05;

/**
 * 撤退ポイントを地面の破線の円で出す。
 * 色は既存パレットのビーム射線の色（#6fe6ff）。機体のリングと混ざらないよう、破線とゆっくりした点滅で区別する。
 */
export function RetreatPointMarker({ point }: { point: RetreatPointView }) {
    const radius = point.radius * POSITION_SCALE;
    const lineRef = useRef<THREE.LineLoop>(null);

    const line = useMemo(() => {
        const points: THREE.Vector3[] = [];
        for (let i = 0; i < SEGMENTS; i++) {
            const a = (i / SEGMENTS) * Math.PI * 2;
            points.push(new THREE.Vector3(Math.cos(a) * radius, 0, Math.sin(a) * radius));
        }
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineDashedMaterial({
            color: HIT_EFFECT_COLORS.tracerBeam,
            dashSize: 1.2,
            gapSize: 0.8,
            transparent: true,
            opacity: 0.9,
        });
        const loop = new THREE.LineLoop(geometry, material);
        loop.computeLineDistances();
        return loop;
    }, [radius]);

    useFrame((state) => {
        if (!lineRef.current) return;
        // 2 秒周期でゆっくり明滅させる
        (lineRef.current.material as THREE.LineDashedMaterial).opacity =
            0.65 + Math.sin(state.clock.elapsedTime * Math.PI) * 0.3;
    });

    return (
        <group
            position={[
                point.position.x * POSITION_SCALE,
                point.position.y * POSITION_SCALE + GROUND_LIFT,
                point.position.z * POSITION_SCALE,
            ]}
        >
            <primitive object={line} ref={lineRef} />
            {/* 範囲の内側をうっすら塗って、地面の目印として読めるようにする */}
            <mesh rotation={[-Math.PI / 2, 0, 0]}>
                <circleGeometry args={[radius, SEGMENTS]} />
                <meshBasicMaterial
                    color={HIT_EFFECT_COLORS.tracerBeam}
                    transparent
                    opacity={0.08}
                    side={THREE.DoubleSide}
                    depthWrite={false}
                />
            </mesh>
            <Html center position={[0, 1.5, 0]}>
                <div
                    className="pointer-events-none select-none whitespace-nowrap text-[10px] font-bold px-1.5 py-0.5 bg-black/70"
                    style={{
                        color: HIT_EFFECT_COLORS.tracerBeam,
                        border: `1px dashed ${HIT_EFFECT_COLORS.tracerBeam}`,
                    }}
                >
                    撤退ポイント
                </div>
            </Html>
        </group>
    );
}
