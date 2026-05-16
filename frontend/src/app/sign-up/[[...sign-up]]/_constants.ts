import backgroundsData from "@/data/backgrounds.json";
import type { Faction, Background, BonusAllocation, StatKey } from "@/app/onboarding/_types";

/** 選択可能なパイロット経歴の一覧 */
export const BACKGROUNDS: Background[] = backgroundsData as Background[];

/** ボーナスポイントの合計配布数 */
export const BONUS_POINTS_TOTAL = 5;

/** ステータスポイントを割り振れるステータスキーの一覧 */
export const STAT_KEYS: StatKey[] = ["DEX", "INT", "REF", "TOU", "LUK"];

/** 各ステータスの日本語説明文 */
export const STAT_DESCRIPTIONS: Record<StatKey, string> = {
  DEX: "器用 (DEX): 手先の器用さ",
  INT: "直感 (INT): 状況判断力",
  REF: "反応 (REF): 反射神経",
  TOU: "耐久 (TOU): 体力・頑丈さ",
  LUK: "幸運 (LUK): 運の良さ",
};

/** ボーナス割り振りの初期状態（全ステータス0） */
export const INITIAL_BONUS: BonusAllocation = {
  DEX: 0,
  INT: 0,
  REF: 0,
  TOU: 0,
  LUK: 0,
};

/** 勢力ごとの初期配備機体名 */
export const FACTION_UNIT_NAME: Record<Faction, string> = {
  FEDERATION: "RGM-79T GM Trainer",
  ZEON: "MS-06T Zaku II Trainer",
};

/** フェーズインジケーターに表示するフェーズ名 */
export const PHASE_LABELS = [
  "勢力選択",
  "連絡先入力",
  "認証確認",
  "パイロット申告",
  "入隊許可証",
];

/** ウィザードのフェーズ番号（1〜5） */
export type WizardPhase = 1 | 2 | 3 | 4 | 5;

/** UIテーマバリアント（勢力に対応: ZEON=secondary, FEDERATION=accent） */
export type ThemeVariant = "secondary" | "accent";

/** テーマバリアントに対応する説明テキストの色クラスを返す */
export function themeTextClass(v: ThemeVariant): string {
  return v === "accent" ? "text-[#00f0ff]/70" : "text-[#ffb000]/70";
}

/** テーマバリアントに対応するラベルテキストの色クラスを返す */
export function themeLabelClass(v: ThemeVariant): string {
  return v === "accent" ? "text-[#00f0ff]/80" : "text-[#ffb000]/80";
}

/** テーマバリアントに対応するボーダー＋背景クラスを返す */
export function themeBorderBgClass(v: ThemeVariant): string {
  return v === "accent"
    ? "border-[#00f0ff]/40 bg-[#00f0ff]/5"
    : "border-[#ffb000]/40 bg-[#ffb000]/5";
}
