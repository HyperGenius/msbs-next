/* frontend/src/components/BattleViewer/scene/DestroyedExplosion.tsx */

"use client";

import type { CSSProperties } from "react";
import { Html } from "@react-three/drei";

const POSITION_SCALE = 0.05;

/** 爆発の長さ（ミリ秒）。バナーはこの後に開く。 */
export const EXPLOSION_DURATION_MS = 1100;

const CORE_SIZE_PX = 90;
const RING_SIZE_PX = 220;
const DEBRIS_COUNT = 14;
const DEBRIS_LENGTH_PX = 22;

interface DestroyedExplosionProps {
    position: { x: number; y: number; z: number };
}

/**
 * 撃破された機体の位置で爆発を一度だけ再生する。
 * 表示した時点から始まり、終わると透明のまま残る。巻き戻して外すと、次に出したときに最初から再生する。
 */
export function DestroyedExplosion({ position }: DestroyedExplosionProps) {
    return (
        <Html position={[position.x * POSITION_SCALE, position.y * POSITION_SCALE, position.z * POSITION_SCALE]} center>
            <div className="pointer-events-none select-none relative w-0 h-0">
                <div
                    className="absolute left-0 top-0 rounded-full"
                    style={{
                        width: CORE_SIZE_PX,
                        height: CORE_SIZE_PX,
                        background: "radial-gradient(circle, #fff 0%, #ffd84a 35%, #ff6a1a 65%, rgba(255,60,0,0) 100%)",
                        animation: `bv-explosion-core ${EXPLOSION_DURATION_MS * 0.7}ms ease-out both`,
                    }}
                />
                <div
                    className="absolute left-0 top-0 rounded-full"
                    style={{
                        width: RING_SIZE_PX,
                        height: RING_SIZE_PX,
                        border: "3px solid #ffb04a",
                        animation: `bv-explosion-ring ${EXPLOSION_DURATION_MS}ms ease-out both`,
                    }}
                />
                {Array.from({ length: DEBRIS_COUNT }, (_, i) => (
                    <div
                        key={i}
                        className="absolute left-0 top-0 rounded-full"
                        style={{
                            "--bv-debris-angle": `${(360 / DEBRIS_COUNT) * i + (i % 3) * 9}deg`,
                            "--bv-debris-distance": `${70 + (i % 4) * 18}px`,
                            width: DEBRIS_LENGTH_PX,
                            height: 3,
                            background: "linear-gradient(90deg, #ffd84a, rgba(255,106,26,0))",
                            transformOrigin: "0 50%",
                            animation: `bv-explosion-debris ${EXPLOSION_DURATION_MS}ms ease-out both`,
                        } as CSSProperties}
                    />
                ))}
            </div>
        </Html>
    );
}
