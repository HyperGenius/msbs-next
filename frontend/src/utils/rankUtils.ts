/* frontend/src/utils/rankUtils.ts */
import { MobileSuit } from "@/types/battle";

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

/**
 * 地形適正ランク（S〜D）に対応する補正値文字列を返す.
 */
export function getRankModifier(rank: string): string {
  switch (rank) {
    case "S": return "+20%";
    case "A": return "±0%";
    case "B": return "-20%";
    case "C": return "-40%";
    case "D": return "-60%";
    default:  return "±0%";
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
  weapon_power: [
    { rank: "S", min: 300 },
    { rank: "A", min: 200 },
    { rank: "B", min: 150 },
    { rank: "C", min: 100 },
    { rank: "D", min: 50 },
    { rank: "E", min: 0 },
  ],
  weapon_range: [
    { rank: "S", min: 600 },
    { rank: "A", min: 500 },
    { rank: "B", min: 400 },
    { rank: "C", min: 300 },
    { rank: "D", min: 200 },
    { rank: "E", min: 0 },
  ],
  weapon_accuracy: [
    { rank: "S", min: 90 },
    { rank: "A", min: 80 },
    { rank: "B", min: 70 },
    { rank: "C", min: 60 },
    { rank: "D", min: 50 },
    { rank: "E", min: 0 },
  ],
};

function lookupRank(statName: string, value: number): string {
  const table = THRESHOLDS[statName];
  if (!table) return "C";
  for (const entry of table) {
    if (value >= entry.min) return entry.rank;
  }
  return "E";
}

/**
 * ステータス値をランク文字列（S〜E）に変換する.
 * バックエンドと同じ閾値テーブルを使用。
 */
export function getRank(statName: "hp" | "armor" | "mobility", value: number): string {
  return lookupRank(statName, value);
}

/**
 * 武器パラメータ値をランク文字列（S〜E）に変換する.
 * バックエンドと同じ閾値テーブルを使用。
 * ショップ画面などランクフィールドが付与されていない場合のフォールバックとして使用する。
 */
export function getWeaponRank(
  statName: "weapon_power" | "weapon_range" | "weapon_accuracy",
  value: number
): string {
  return lookupRank(statName, value);
}

/** 最適射程の距離ラベルと色クラス */
export interface OptimalRangeDisplayInfo {
  label: string;
  colorClass: string;
}

/**
 * 最適射程（m）を距離カテゴリに変換する.
 * ≤ 200m: 近距離 / ≤ 400m: 中距離 / > 400m: 遠距離
 */
export function getOptimalRangeLabel(value: number): OptimalRangeDisplayInfo {
  if (value <= 200) return { label: "近距離", colorClass: "text-orange-400" };
  if (value <= 400) return { label: "中距離", colorClass: "text-yellow-400" };
  return { label: "遠距離", colorClass: "text-blue-400" };
}

/**
 * 減衰率（0〜1 の小数）をランク文字列（S〜E）に変換する.
 * 値が小さいほど高ランク（S = 減衰しない、E = 高減衰率）。
 */
export function getDecayRateRank(value: number): string {
  if (value <= 0.02) return "S";
  if (value <= 0.05) return "A";
  if (value <= 0.10) return "B";
  if (value <= 0.20) return "C";
  if (value <= 0.30) return "D";
  return "E";
}

/** 地形環境ごとのアイコンとラベル */
const TERRAIN_META: Record<string, { icon: string; label: string }> = {
  SPACE:      { icon: "🌌", label: "宇宙" },
  GROUND:     { icon: "🏔️", label: "地上" },
  COLONY:     { icon: "🏢", label: "コロニー" },
  UNDERWATER: { icon: "🌊", label: "水中" },
};

/** 地形適正1件分のUI表示情報 */
export interface TerrainDisplayInfo {
  rank: string;
  colorClass: string;
  modifier: string;
  icon: string;
  label: string;
}

/** MobileSuit の UI 表示用サマリー */
export interface MobileSuitDisplayInfo {
  terrain: Record<string, TerrainDisplayInfo>;
  hp: { rank: string; colorClass: string };
  armor: { rank: string; colorClass: string };
  mobility: { rank: string; colorClass: string };
}

/** MobileSuit を拡張した UI 表示用の型 */
export interface EnrichedMobileSuit extends MobileSuit {
  display: MobileSuitDisplayInfo;
}

/**
 * 地形環境キーとランク文字列から UI 表示情報を生成する.
 */
export function getTerrainDisplayInfo(env: string, rank: string): TerrainDisplayInfo {
  const meta = TERRAIN_META[env] ?? { icon: "❓", label: env };
  return {
    rank,
    colorClass: getRankColor(rank),
    modifier: getRankModifier(rank),
    icon: meta.icon,
    label: meta.label,
  };
}

/**
 * 生の MobileSuit オブジェクトを受け取り、UI 表示用の装飾データが付与された
 * EnrichedMobileSuit を返す.
 */
export function enrichMobileSuit(ms: MobileSuit): EnrichedMobileSuit {
  const terrainKeys = ["SPACE", "GROUND", "COLONY", "UNDERWATER"];
  const terrain: Record<string, TerrainDisplayInfo> = {};
  for (const env of terrainKeys) {
    const rank = ms.terrain_adaptability?.[env] ?? "A";
    terrain[env] = getTerrainDisplayInfo(env, rank);
  }

  const hpRank = ms.hp_rank ?? getRank("hp", ms.max_hp);
  const armorRank = ms.armor_rank ?? getRank("armor", ms.armor);
  const mobilityRank = ms.mobility_rank ?? getRank("mobility", ms.mobility);

  return {
    ...ms,
    display: {
      terrain,
      hp:       { rank: hpRank,       colorClass: getRankColor(hpRank) },
      armor:    { rank: armorRank,     colorClass: getRankColor(armorRank) },
      mobility: { rank: mobilityRank,  colorClass: getRankColor(mobilityRank) },
    },
  };
}
