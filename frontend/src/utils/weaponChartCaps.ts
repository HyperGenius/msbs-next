/**
 * 武器購入詳細モーダルのレーダーチャート正規化に使う固定値（全武器共通）。
 *
 * admin-tool の WeaponRadarChart は「全武器の最大値」で動的正規化するが、
 * 購入画面では単体武器のみを表示するため、代わりにこの固定上限を基準にする。
 */
export const WEAPON_CHART_CAPS = {
  power: 1000,
  range: 1000,
  accuracy: 120,
  optimal_range: 1000,
} as const;

/**
 * 減衰率は値が小さいほど高性能なため、他の軸と異なり単純な上限比ではなく
 * 「best（最良値）〜worst（最悪値）」の範囲でチャート上のスコア(0〜100)を算出する。
 * best（0.01）でスコア100、worst（0.25）でスコア0になる。
 */
export const DECAY_RATE_CHART_RANGE = {
  best: 0.01,
  worst: 0.25,
} as const;
