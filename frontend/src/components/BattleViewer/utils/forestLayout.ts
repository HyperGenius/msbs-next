/* frontend/src/components/BattleViewer/utils/forestLayout.ts */

import { Obstacle } from "@/types/battle";

/** 木立の 1 本分の配置（シーン座標）。 */
export interface TreePlacement {
    obstacleId: string;
    x: number;
    y: number;
    z: number;
    height: number;
    canopyRadius: number;
    /** 樹冠の色の候補（FOREST_CANOPY_COLORS）の添字。 */
    shade: number;
}

/** 木立の面積（シーン単位²）あたりの木の本数。 */
const TREES_PER_AREA = 0.06;
export const MIN_TREES_PER_GROVE = 3;
// スマートフォンでの描画負荷を抑えるための上限。DENSE の障害物数でも合計 1000 本を超えない。
export const MAX_TREES_PER_GROVE = 9;
export const FOREST_CANOPY_SHADES = 3;
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

/** 文字列から 32bit のシード値を作る（FNV-1a）。 */
function hashString(value: string): number {
    let hash = 0x811c9dc5;
    for (let i = 0; i < value.length; i++) {
        hash ^= value.charCodeAt(i);
        hash = Math.imul(hash, 0x01000193);
    }
    return hash >>> 0;
}

/** シード付きの疑似乱数（mulberry32）。0 以上 1 未満を返す。 */
function seededRandom(seed: number): () => number {
    let state = seed;
    return () => {
        state = (state + 0x6d2b79f5) >>> 0;
        let t = state;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

export function getTreeCount(radius: number): number {
    const count = Math.round(Math.PI * radius * radius * TREES_PER_AREA);
    return Math.min(MAX_TREES_PER_GROVE, Math.max(MIN_TREES_PER_GROVE, count));
}

/**
 * 障害物の半径の範囲に木を並べる。
 * 配置は obstacle_id から決まる。再描画やリプレイのたびに木が動かないようにするため。
 * @param scale シミュレーション座標（m）からシーン座標への倍率
 */
export function layoutGrove(obstacle: Obstacle, scale: number): TreePlacement[] {
    const random = seededRandom(hashString(obstacle.obstacle_id));
    const radius = obstacle.radius * scale;
    const groveHeight = Math.max(obstacle.height * scale, radius * 2);
    const count = getTreeCount(radius);
    // 樹冠の合計面積が木立の面積とほぼ同じになる半径。木の間から地面が少し見える。
    const canopyRadius = radius / Math.sqrt(count);
    const startAngle = random() * Math.PI * 2;

    const trees: TreePlacement[] = [];
    for (let i = 0; i < count; i++) {
        // ひまわりの種の配置。円内に偏りなく並ぶ。樹冠がはみ出さないよう外周を詰める。
        const distance = Math.sqrt((i + 0.5) / count) * Math.max(0, radius - canopyRadius * 0.6);
        const angle = startAngle + i * GOLDEN_ANGLE;
        trees.push({
            obstacleId: obstacle.obstacle_id,
            x: obstacle.position.x * scale + Math.cos(angle) * distance,
            y: obstacle.position.y * scale,
            z: obstacle.position.z * scale + Math.sin(angle) * distance,
            height: groveHeight * (0.7 + random() * 0.3),
            canopyRadius: canopyRadius * (0.85 + random() * 0.3),
            shade: Math.floor(random() * FOREST_CANOPY_SHADES),
        });
    }
    return trees;
}
