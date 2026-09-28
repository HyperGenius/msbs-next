/* frontend/src/utils/theater.ts */
import {
  BattleResult,
  MinovskyLevel,
  MobileSuit,
  TheaterForecast,
} from "@/types/battle";

type TheaterFields = Pick<
  BattleResult,
  "theater_name" | "environment_name" | "minovsky_density"
>;

/**
 * 戦域の表示名を返す（例: 「ソロモン宙域（宇宙）／ミノフスキー濃度 42%」）。
 * 戦域の無いバトルは null を返す。
 */
export function formatTheaterLabel(battle: TheaterFields): string | null {
  if (!battle.theater_name) return null;
  const environment = battle.environment_name
    ? `（${battle.environment_name}）`
    : "";
  const minovsky =
    battle.minovsky_density != null
      ? `／ミノフスキー濃度 ${Math.round(battle.minovsky_density * 100)}%`
      : "";
  return `${battle.theater_name}${environment}${minovsky}`;
}

/** BattleViewer に渡す環境を返す。描画プリセットが無いバトルは環境タイプIDを使う。 */
export function getViewerEnvironment(
  battle: Pick<BattleResult, "viewer_preset" | "environment">,
): string {
  return battle.viewer_preset ?? battle.environment ?? "SPACE";
}

/** 予報カードの環境ごとのアイコンと色 */
export interface EnvironmentVisual {
  icon: string;
  textClass: string;
  borderClass: string;
}

const ENVIRONMENT_VISUALS: Record<string, EnvironmentVisual> = {
  SPACE: {
    icon: "🌌",
    textClass: "text-[#00f0ff]",
    borderClass: "border-[#00f0ff]/50",
  },
  FOREST: {
    icon: "🌲",
    textClass: "text-emerald-400",
    borderClass: "border-emerald-400/50",
  },
};

const DEFAULT_ENVIRONMENT_VISUAL: EnvironmentVisual = {
  icon: "🛰️",
  textClass: "text-[#00ff41]",
  borderClass: "border-[#00ff41]/30",
};

/** 環境タイプのアイコンと色を返す。未知の環境タイプは既定の見た目にする。 */
export function getEnvironmentVisual(environmentId: string): EnvironmentVisual {
  return ENVIRONMENT_VISUALS[environmentId] ?? DEFAULT_ENVIRONMENT_VISUAL;
}

const MINOVSKY_LEVEL_LABELS: Record<MinovskyLevel, string> = {
  LOW: "低",
  MEDIUM: "中",
  HIGH: "高",
};

/** ミノフスキー濃度の段階の表示名を返す */
export function getMinovskyLevelLabel(level: MinovskyLevel): string {
  return MINOVSKY_LEVEL_LABELS[level] ?? level;
}

/**
 * 予報の環境での機体の地形適正を返す。
 * 機体に設定が無い環境は、バックエンドと同じく環境タイプの既定ランクを使う。
 */
export function getTerrainGradeFor(
  mobileSuit: Pick<MobileSuit, "terrain_adaptability">,
  forecast: Pick<TheaterForecast, "environment_id" | "default_terrain_grade">,
): string {
  return (
    mobileSuit.terrain_adaptability?.[forecast.environment_id] ??
    forecast.default_terrain_grade
  );
}

const UNSUITABLE_TERRAIN_GRADES = new Set(["C", "D"]);

/** 開催予定時刻を JST の「10/2(金)」の形式にする。開催日は JST で決まるため。 */
export function formatForecastDate(scheduledAt: string): string {
  const parts = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    month: "numeric",
    day: "numeric",
    weekday: "short",
  }).formatToParts(new Date(scheduledAt));
  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((p) => p.type === type)?.value ?? "";
  return `${get("month")}/${get("day")}(${get("weekday")})`;
}

/** 地形適正がその戦域に不向きなランク（C 以下）か */
export function isUnsuitableTerrainGrade(grade: string): boolean {
  return UNSUITABLE_TERRAIN_GRADES.has(grade);
}
