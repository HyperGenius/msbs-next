/* frontend/src/components/BattleViewer/ui/MinovskyHaze.tsx */

"use client";

import { getMinovskyHazeOpacity } from "../utils";

const NOISE_TILE_PX = 256;
// SVG のノイズは画像として 1 回だけラスタライズされる。
// 3D パーティクルより軽く、スマートフォンでも負荷がほぼ増えない。
const MIST_NOISE = svgNoise(3, 3, "0 0 0 0 0.8  0 0 0 0 0.9  0 0 0 0 0.85  0 0 0 1.2 -0.35");
const SPECKLE_NOISE = svgNoise(218, 1, "0 0 0 0 0.9  0 0 0 0 1  0 0 0 0 0.95  2.4 0 0 0 -1.6");

/**
 * タイル状に敷ける SVG ノイズを作る。
 * stitchTiles はタイル内の周期数が整数のときだけ継ぎ目を消せるため、周期数で指定する。
 * フィルタ領域の既定値は図形の 120% なので、タイルと同じ大きさに揃える。
 */
function svgNoise(cyclesPerTile: number, octaves: number, colorMatrix: string): string {
    const baseFrequency = cyclesPerTile / NOISE_TILE_PX;
    const svg =
        `<svg xmlns='http://www.w3.org/2000/svg' width='${NOISE_TILE_PX}' height='${NOISE_TILE_PX}'>` +
        `<filter id='n' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' baseFrequency='${baseFrequency}' numOctaves='${octaves}' stitchTiles='stitch'/>` +
        `<feColorMatrix values='${colorMatrix}'/></filter>` +
        `<rect width='100%' height='100%' filter='url(#n)'/></svg>`;
    return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

/**
 * ミノフスキー粒子のもやを画面全体に重ねる。
 * 濃度が高いほど濃くなり、濃度 0 では何も描画しない。
 */
export function MinovskyHaze({ density }: { density?: number | null }) {
    const opacity = getMinovskyHazeOpacity(density);
    if (opacity <= 0) return null;

    return (
        <div
            className="absolute inset-0 overflow-hidden pointer-events-none"
            style={{ opacity }}
            data-testid="minovsky-haze"
            aria-hidden="true"
        >
            <div
                className="bv-minovsky-drift absolute -inset-[64px]"
                style={{ backgroundImage: MIST_NOISE, backgroundSize: "512px 512px" }}
            />
            <div
                className="bv-minovsky-drift-fast absolute -inset-[64px] mix-blend-screen"
                style={{ backgroundImage: SPECKLE_NOISE, backgroundSize: "256px 256px" }}
            />
        </div>
    );
}
