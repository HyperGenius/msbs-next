/* frontend/src/components/BattleViewer/types.ts */

// 警告アイコンの種類
export type WarningType = 'ammo' | 'energy' | 'cooldown';

// バトルイベント効果の種類
export interface BattleEventEffect {
    type: 'critical' | 'resist' | 'guard' | 'damage';
    text: string;
    color: string;
}
