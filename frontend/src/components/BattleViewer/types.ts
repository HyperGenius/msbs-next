/* frontend/src/components/BattleViewer/types.ts */

// 警告アイコンの種類
export type WarningType = 'ammo' | 'energy' | 'cooldown';

// バトルイベント効果の種類
export interface BattleEventEffect {
    type: 'critical' | 'resist' | 'guard' | 'damage' | 'miss' | 'attack_line';
    text: string;
    color: string;
    /** 武器名（表示用） */
    weaponName?: string;
    /** 攻撃ライン描画用ターゲット位置 */
    targetPos?: { x: number; y: number; z: number };
    /** 命中フラグ（true: 命中, false: ミス） */
    hit?: boolean;
}
