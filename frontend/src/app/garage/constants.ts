/* frontend/src/app/garage/constants.ts */

/** 機体に weapon_slot_count が未設定の場合のデフォルトスロット数（既存の2枠機体との後方互換） */
export const DEFAULT_WEAPON_SLOT_COUNT = 2;

export interface WeaponSlot {
  index: number;
  label: string;
  labelJa: string;
}

/**
 * スロットindexから部位ラベルを生成する（0=右腕, 1=左腕, 2以降=ラックN）。
 * バックエンドの `WEAPON_SLOT_ROLE_*`（`backend/app/engine/constants.py`）と対応関係を揃えている（Issue #502）。
 */
function slotLabel(index: number): { label: string; labelJa: string } {
  if (index === 0) return { label: "Right Arm", labelJa: "右腕" };
  if (index === 1) return { label: "Left Arm", labelJa: "左腕" };
  const rackNumber = index - 1;
  return { label: `Rack ${rackNumber}`, labelJa: `ラック${rackNumber}` };
}

/**
 * スロットindex単体から部位ラベル（日本語）を返す。
 * 装備済みスロットの表示（`equipped_slot`）のように、スロット総数を知らなくても
 * ラベルを解決したい箇所で使う（部位ロールはindexのみに依存するため）。
 */
export function getWeaponSlotLabel(index: number): string {
  return slotLabel(index).labelJa;
}

/**
 * 機体の weapon_slot_count に応じた武器スロット定義を生成する。
 * 値が未設定・不正な場合は DEFAULT_WEAPON_SLOT_COUNT にフォールバックする。
 */
export function getWeaponSlots(weaponSlotCount?: number): WeaponSlot[] {
  const slotCount =
    weaponSlotCount && weaponSlotCount > 0
      ? weaponSlotCount
      : DEFAULT_WEAPON_SLOT_COUNT;

  return Array.from({ length: slotCount }, (_, index) => ({
    index,
    ...slotLabel(index),
  }));
}
