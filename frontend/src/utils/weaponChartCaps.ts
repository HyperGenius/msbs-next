/**
 * 武器購入詳細モーダルのレーダーチャート正規化に使う上限値（全武器共通・固定値）。
 *
 * admin-tool の WeaponRadarChart は「全武器の最大値」で動的正規化するが、
 * 購入画面では単体武器のみを表示するため、代わりにこの固定上限を基準にする。
 * decay_rate は値が小さいほど高性能なため、他の軸と逆に「小さいほどチャート上で伸びる」向きで使う。
 */
export const WEAPON_CHART_CAPS = {
  power: 1000,
  range: 1000,
  accuracy: 120,
  optimal_range: 1000,
  decay_rate: 0.01,
} as const;
