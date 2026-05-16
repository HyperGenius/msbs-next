/* frontend/src/components/BattleViewer/utils/losUtils.ts */
// バックエンド combat.py の has_los と同じ Ray-Sphere 交差判定をTypeScriptで実装

import { Obstacle } from "@/types/battle";

/**
 * 2点間の視線（Line of Sight）が障害物で遮断されているかを判定する。
 * バックエンドの `has_los`（Ray-Sphere 交差判定）と同一アルゴリズム。
 *
 * @param posA - 視線の始点（シミュレーション実座標）
 * @param posB - 視線の終点（シミュレーション実座標）
 * @param obstacles - フィールド上の障害物リスト
 * @returns { clear: boolean; blockedBy: string | null }
 *   - clear: true なら視線が通っている、false なら遮断されている
 *   - blockedBy: 遮断している障害物の obstacle_id（遮断なしの場合は null）
 */
export function hasLos(
    posA: { x: number; y: number; z: number },
    posB: { x: number; y: number; z: number },
    obstacles: Obstacle[]
): { clear: boolean; blockedBy: string | null } {
    if (!obstacles.length) return { clear: true, blockedBy: null };

    const dx = posB.x - posA.x;
    const dy = posB.y - posA.y;
    const dz = posB.z - posA.z;
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
    if (dist < 1e-6) return { clear: true, blockedBy: null };

    const udx = dx / dist;
    const udy = dy / dist;
    const udz = dz / dist;

    for (const obs of obstacles) {
        const ocx = posA.x - obs.position.x;
        const ocy = posA.y - obs.position.y;
        const ocz = posA.z - obs.position.z;
        const b = 2.0 * (ocx * udx + ocy * udy + ocz * udz);
        const c = ocx * ocx + ocy * ocy + ocz * ocz - obs.radius * obs.radius;
        const discriminant = b * b - 4.0 * c;
        if (discriminant < 0) continue;
        const t = (-b - Math.sqrt(discriminant)) / 2.0;
        if (t > 0.0 && t < dist) {
            return { clear: false, blockedBy: obs.obstacle_id };
        }
    }
    return { clear: true, blockedBy: null };
}
