/* frontend/src/app/garage/utils.ts */
import { Weapon } from "@/types/battle";

/**
 * 武器パラメータの差分を計算する
 */
export function calcWeaponDiff(
  current: Weapon | undefined,
  candidate: Weapon
): { power: number; range: number; accuracy: number } {
  return {
    power: candidate.power - (current?.power ?? 0),
    range: candidate.range - (current?.range ?? 0),
    accuracy: candidate.accuracy - (current?.accuracy ?? 0),
  };
}

/**
 * 差分値の色クラスを返す
 */
export function diffColor(val: number): string {
  if (val > 0) return "text-green-400";
  if (val < 0) return "text-red-400";
  return "text-gray-400";
}

/**
 * 差分値の表示文字列を返す
 */
export function diffText(val: number): string {
  if (val > 0) return `+${val}`;
  if (val < 0) return `${val}`;
  return "±0";
}
