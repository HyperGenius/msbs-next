/* frontend/src/app/garage/weaponUpgrade.ts */

import { PlayerWeapon, Weapon, WeaponUpgradeStatType } from "@/types/battle";

export interface WeaponStatInfo {
  label: string;
  key: WeaponUpgradeStatType;
  rankStatName: "weapon_power" | "weapon_accuracy";
  getBase: (pw: PlayerWeapon) => number;
  getBonus: (pw: PlayerWeapon) => number;
  increment: number;
  /** 実効値(base+bonus)がこの倍率(base × capMultiplier)に達するまで改造可能 */
  capMultiplier: number;
  baseCost: number;
  costDivisor: number;
}

// バックエンド(WeaponEngineeringService)の _STAT_CONFIGS と同じ定義
export const WEAPON_UPGRADE_STATS: WeaponStatInfo[] = [
  {
    label: "威力",
    key: "power_bonus",
    rankStatName: "weapon_power",
    getBase: (pw) => (pw.base_snapshot as { power?: number }).power ?? 0,
    getBonus: (pw) => pw.custom_stats?.power_bonus ?? 0,
    increment: 5,
    capMultiplier: 2.0,
    baseCost: 60,
    costDivisor: 30,
  },
  {
    label: "命中率",
    key: "accuracy_bonus",
    rankStatName: "weapon_accuracy",
    getBase: (pw) => (pw.base_snapshot as { accuracy?: number }).accuracy ?? 0,
    getBonus: (pw) => pw.custom_stats?.accuracy_bonus ?? 0,
    increment: 1.0,
    capMultiplier: 1.3,
    baseCost: 100,
    costDivisor: 5,
  },
];

/** バックエンドと同じコスト計算式（ボーナス値ベース） */
export function calcStepCost(stat: WeaponStatInfo, bonus: number): number {
  return Math.floor(stat.baseCost * (1 + bonus / stat.costDivisor));
}

/** ボーナス値の上限（実効値が base × capMultiplier に達するまで） */
export function bonusCap(stat: WeaponStatInfo, base: number): number {
  return base * (stat.capMultiplier - 1);
}

/** N ステップ分の累積コストとシミュレーション後のボーナス値を計算 */
export function simulateSteps(
  stat: WeaponStatInfo,
  base: number,
  currentBonus: number,
  steps: number
): { totalCost: number; finalBonus: number } {
  const cap = bonusCap(stat, base);
  let bonus = currentBonus;
  let totalCost = 0;
  for (let i = 0; i < steps; i++) {
    if (bonus >= cap) break;
    totalCost += calcStepCost(stat, bonus);
    bonus = Math.min(bonus + stat.increment, cap);
  }
  return { totalCost, finalBonus: bonus };
}

/** 所持クレジットで何ステップ踏めるか（上限: cap まで）を計算 */
export function calcMaxAffordableSteps(
  stat: WeaponStatInfo,
  base: number,
  currentBonus: number,
  credits: number
): number {
  const cap = bonusCap(stat, base);
  let bonus = currentBonus;
  let remaining = credits;
  let steps = 0;
  while (bonus < cap) {
    const cost = calcStepCost(stat, bonus);
    if (remaining < cost) break;
    remaining -= cost;
    bonus = Math.min(bonus + stat.increment, cap);
    steps++;
  }
  return steps;
}

// 浮動小数の誤差で ceil が 1 段多く数えないようにするための許容誤差
const STEP_COUNT_EPSILON = 1e-6;

/**
 * 全ステータスの改造済み段階数の合計を返す。
 * 最後の 1 段は上限で切り詰められて increment に満たないことがあるため、切り上げで数える。
 */
export function countUpgradeSteps(pw: PlayerWeapon): number {
  return WEAPON_UPGRADE_STATS.reduce((sum, stat) => {
    const bonus = stat.getBonus(pw);
    if (bonus <= 0) return sum;
    return sum + Math.ceil(bonus / stat.increment - STEP_COUNT_EPSILON);
  }, 0);
}

/** base_snapshot に custom_stats の改造差分（power_bonus/accuracy_bonus）をマージした実効スペックを解決する */
export function resolveWeaponSpec(pw: PlayerWeapon): Weapon {
  const base = pw.base_snapshot as unknown as Weapon;
  const powerBonus = pw.custom_stats?.power_bonus ?? 0;
  const accuracyBonus = pw.custom_stats?.accuracy_bonus ?? 0;
  if (powerBonus === 0 && accuracyBonus === 0) return base;
  return {
    ...base,
    power: base.power + powerBonus,
    accuracy: base.accuracy + accuracyBonus,
  };
}
