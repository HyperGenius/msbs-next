/* frontend/src/utils/displayUtils.ts */

/** モビルスーツのステータス項目名 */
export const STATUS_LABELS = {
  max_hp: "最大耐久",
  hp: "最大耐久",
  armor: "装甲",
  mobility: "機動性",
  sensor_range: "索敵範囲",
  beam_resistance: "対ビーム防御",
  physical_resistance: "対実弾防御",
  melee_aptitude: "格闘適性",
  shooting_aptitude: "射撃適性",
  accuracy_bonus: "命中補正",
  evasion_bonus: "回避補正",
  acceleration_bonus: "加速補正",
  turning_bonus: "旋回補正",
  max_en: "最大EN",
  en_recovery: "EN回復",
  max_propellant: "最大推進剤",
} as const;

/** 武器のステータス項目名 */
export const WEAPON_LABELS = {
  type: "属性",
  power: "威力",
  range: "射程",
  accuracy: "命中率",
  optimal_range: "最適射程",
  decay_rate: "減衰率",
  max_ammo: "弾数",
  en_cost: "EN消費",
  cool_down_turn: "クールダウン",
} as const;

/** パイロットのステータス項目名 */
export const PILOT_LABELS = {
  level: "レベル",
  wins: "勝利数",
  losses: "敗北数",
  kills: "総撃破数",
  win_rate: "勝率",
} as const;
