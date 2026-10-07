/* frontend/src/components/BattleViewer/types.ts */

// 警告アイコンの種類
export type WarningType = 'ammo' | 'cooldown';

/** 射線の描き方。BEAM は伸びる直線、BULLET は飛んでいく短い弾体。 */
export type TracerKind = 'BEAM' | 'BULLET';

/** 着弾側で何が起きたか。`clash` は鍔迫り合いで、両機の中間に出す。 */
export type ImpactKind = 'hit' | 'critical' | 'combo' | 'miss' | 'clash';

/** 1 件の攻撃（ATTACK / MISS / MELEE_COMBO / MELEE_CLASH ログ 1 件）から作る演出データ。 */
export interface AttackEvent {
    attackerId: string;
    targetId: string;
    weaponName?: string;
    tracerKind: TracerKind;
    impact: ImpactKind;
    /** MISS と鍔迫り合いのときは 0。 */
    damage: number;
    /** 鍔迫り合いで相手が使った武器。 */
    targetWeaponName?: string;
    comboCount?: number;
    /** 装甲による軽減率（%）。軽減が無いときは undefined。 */
    resistPercent?: number;
}
