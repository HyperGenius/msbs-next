/* frontend/src/app/garage/constants.ts */

/** 機体に weapon_slot_count が未設定の場合のデフォルトスロット数（既存の2枠機体との後方互換） */
export const DEFAULT_WEAPON_SLOT_COUNT = 2;

export interface WeaponSlot {
  index: number;
  label: string;
  labelJa: string;
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
    label: `Slot ${index + 1}`,
    labelJa: `スロット${index + 1}`,
  }));
}
