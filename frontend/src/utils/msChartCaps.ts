/**
 * MS購入詳細モーダルのレーダーチャート正規化に使う固定値（全MS共通、Issue #483）。
 *
 * `weaponChartCaps.ts` と同じ方針: 購入画面では単体MSのみを表示するため、
 * 全MSの実測最大値で動的正規化するのではなく固定上限を基準にする。
 */
export const MS_CHART_CAPS = {
  max_hp: 1500,
  armor: 150,
  mobility: 2.0,
} as const;

/**
 * 射撃適正・格闘適正は 0.5〜1.5 の範囲を取る想定のステータスで、単純な上限比では
 * 下限側（0.5未満）の劣った機体との差が表現できないため、MIN/MAXレンジで
 * チャート上のスコア(0〜100)を算出する。MIN(0.5)でスコア0、MAX(1.5)でスコア100になる。
 */
export const APTITUDE_CHART_RANGE = {
  min: 0.5,
  max: 1.5,
} as const;
