/* frontend/src/utils/rankUtils.ts */

/**
 * ランク文字列（S〜E）に対応するTailwind CSSカラークラスを返す.
 * 地形適正UIと同じカラーコードを使用。
 */
export function getRankColor(rank: string): string {
  switch (rank) {
    case "S": return "text-green-400";
    case "A": return "text-blue-400";
    case "B": return "text-yellow-400";
    case "C": return "text-orange-400";
    case "D": return "text-red-400";
    default:  return "text-gray-400";
  }
}

type RankThreshold = { rank: string; min: number };

/**
 * フロントエンド用の閾値テーブル.
 * バックエンドの backend/data/master/thresholds.json と同じ値を定義する。
 * ショップ画面などバックエンドのランクフィールドが付与されないAPIレスポンス向けに使用する。
 * 閾値を変更する場合は両方を同時に更新すること。
 */
const THRESHOLDS: Record<string, RankThreshold[]> = {
  hp: [
    { rank: "S", min: 2000 },
    { rank: "A", min: 1500 },
    { rank: "B", min: 1000 },
    { rank: "C", min: 700 },
    { rank: "D", min: 400 },
    { rank: "E", min: 0 },
  ],
  armor: [
    { rank: "S", min: 100 },
    { rank: "A", min: 80 },
    { rank: "B", min: 60 },
    { rank: "C", min: 40 },
    { rank: "D", min: 20 },
    { rank: "E", min: 0 },
  ],
  mobility: [
    { rank: "S", min: 2.0 },
    { rank: "A", min: 1.5 },
    { rank: "B", min: 1.2 },
    { rank: "C", min: 0.9 },
    { rank: "D", min: 0.6 },
    { rank: "E", min: 0.0 },
  ],
};

/**
 * ステータス値をランク文字列（S〜E）に変換する.
 * バックエンドと同じ閾値テーブルを使用。
 */
export function getRank(statName: "hp" | "armor" | "mobility", value: number): string {
  const table = THRESHOLDS[statName];
  if (!table) return "C";
  for (const entry of table) {
    if (value >= entry.min) return entry.rank;
  }
  return "E";
}
