/* frontend/src/components/BattleViewer/scene/TracerMesh.tsx */

"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import { TracerKind } from "../types";
import { HIT_EFFECT_COLORS } from "../utils";

const POSITION_SCALE = 0.05;

// ビームは射線全体の表示時間のうち、この割合で伸び切り、この割合からフェードを始める
const BEAM_GROW_RATIO = 0.27;
const BEAM_FADE_START_RATIO = 0.36;
/** 実弾の弾体の長さ（Three.js 座標）。 */
const BULLET_LENGTH = 2;

// 射線は緑のグリッドと重なると埋もれる。
// 暗い縁取り（halo）の上に本体を重ね、ビームは白い芯も足してグリッドと輝度差を付ける。
// 線幅は px。下の層から順に描く。
const TRACER_LAYERS: Record<TracerKind, { width: number; color: "halo" | "body" | "core"; opacity: number }[]> = {
    BEAM: [
        { width: 8, color: "halo", opacity: 0.75 },
        { width: 3.5, color: "body", opacity: 1 },
        { width: 1.2, color: "core", opacity: 1 },
    ],
    BULLET: [
        { width: 7, color: "halo", opacity: 0.75 },
        { width: 3, color: "body", opacity: 1 },
    ],
};
const HALO_COLOR = "#000000";
// グリッド（透過描画）より後に、深度を無視して描く。射線がグリッドや障害物の下に隠れないようにする
const TRACER_RENDER_ORDER = 10;

interface TracerMeshProps {
    from: { x: number; y: number; z: number };
    to: { x: number; y: number; z: number };
    kind: TracerKind;
    color: string;
    /** Date.now() 基準の開始時刻。 */
    startAt: number;
    durationMs: number;
    onComplete: () => void;
}

function toScene(p: { x: number; y: number; z: number }): THREE.Vector3 {
    return new THREE.Vector3(p.x * POSITION_SCALE, p.y * POSITION_SCALE, p.z * POSITION_SCALE);
}

/** 発射側から被弾側への射線。ビームは直線が伸びてフェードし、実弾は短い弾体が飛ぶ。 */
export function TracerMesh({ from, to, kind, color, startAt, durationMs, onComplete }: TracerMeshProps) {
    const groupRef = useRef<THREE.Group>(null);
    // drei の Line は Line2 を返す。線幅はピクセル単位のため、group を拡縮しても太さは変わらない
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const lineRefs = useRef<any[]>([]);
    const completedRef = useRef(false);

    const { from3D, to3D, points } = useMemo(() => {
        const f = toScene(from);
        const t = toScene(to);
        const delta = new THREE.Vector3().subVectors(t, f);
        // ビームは始点から終点まで。実弾は先頭（group の原点）から後ろへ伸びる弾体。
        const end =
            kind === "BEAM"
                ? delta
                : delta.clone().normalize().multiplyScalar(-Math.min(BULLET_LENGTH, delta.length()));
        const linePoints: [number, number, number][] = [[0, 0, 0], [end.x, end.y, end.z]];
        return { from3D: f, to3D: t, points: linePoints };
    }, [from, to, kind]);

    useFrame(() => {
        if (completedRef.current || !groupRef.current) return;
        const t = Math.min(Math.max((Date.now() - startAt) / durationMs, 0), 1);

        if (kind === "BEAM") {
            // 始点を原点にした線を拡大して伸ばす
            groupRef.current.scale.setScalar(Math.min(1, Math.max(t / BEAM_GROW_RATIO, 0.001)));
            const fade = t <= BEAM_FADE_START_RATIO ? 1 : 1 - (t - BEAM_FADE_START_RATIO) / (1 - BEAM_FADE_START_RATIO);
            TRACER_LAYERS.BEAM.forEach((layer, i) => {
                const material = lineRefs.current[i]?.material;
                if (material) material.opacity = layer.opacity * fade;
            });
        } else {
            groupRef.current.position.lerpVectors(from3D, to3D, t);
        }

        if (t >= 1) {
            completedRef.current = true;
            onComplete();
        }
    });

    return (
        <group ref={groupRef} position={from3D} scale={kind === "BEAM" ? 0.001 : 1}>
            {TRACER_LAYERS[kind].map((layer, i) => (
                <Line
                    key={layer.color}
                    ref={(el) => {
                        lineRefs.current[i] = el;
                    }}
                    points={points}
                    color={layer.color === "halo" ? HALO_COLOR : layer.color === "core" ? HIT_EFFECT_COLORS.flashCore : color}
                    lineWidth={layer.width}
                    opacity={layer.opacity}
                    transparent
                    depthTest={false}
                    depthWrite={false}
                    renderOrder={TRACER_RENDER_ORDER + i}
                />
            ))}
        </group>
    );
}
