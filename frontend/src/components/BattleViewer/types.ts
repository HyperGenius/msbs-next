/* frontend/src/components/BattleViewer/types.ts */

// 警告アイコンの種類
export type WarningType = 'ammo' | 'energy' | 'cooldown';

/** 射線の描き方。BEAM は伸びる直線、BULLET は飛んでいく短い弾体。 */
export type TracerKind = 'BEAM' | 'BULLET';

/** 着弾側で何が起きたか。 */
export type ImpactKind = 'hit' | 'critical' | 'combo' | 'miss';

/** 1 件の攻撃（ATTACK / MISS / MELEE_COMBO ログ 1 件）から作る演出データ。 */
export interface AttackEvent {
    attackerId: string;
    targetId: string;
    weaponName?: string;
    tracerKind: TracerKind;
    impact: ImpactKind;
    /** MISS のときは 0。 */
    damage: number;
    comboCount?: number;
    /** 装甲による軽減率（%）。軽減が無いときは undefined。 */
    resistPercent?: number;
}
