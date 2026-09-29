import { z } from "zod";
import {
  MasterEnvironment,
  MasterTheater,
  ObstacleDensity,
  TerrainGrade,
  ViewerPreset,
} from "@/types/admin";

// 選択肢は backend の ObstacleDensity・TerrainGrade・ViewerPreset（models.py）に合わせる。
export const OBSTACLE_DENSITIES: readonly ObstacleDensity[] = ["NONE", "SPARSE", "MEDIUM", "DENSE"];
export const TERRAIN_GRADES: readonly TerrainGrade[] = ["S", "A", "B", "C", "D"];
export const VIEWER_PRESETS: readonly ViewerPreset[] = ["SPACE", "GROUND", "COLONY", "UNDERWATER", "FOREST"];

const obstacleDensitySchema = z.enum(OBSTACLE_DENSITIES as [ObstacleDensity, ...ObstacleDensity[]]);
const terrainGradeSchema = z.enum(TERRAIN_GRADES as [TerrainGrade, ...TerrainGrade[]]);
const viewerPresetSchema = z.enum(VIEWER_PRESETS as [ViewerPreset, ...ViewerPreset[]]);

const numberField = () => z.number({ message: "Must be a number" });

// ============================================================
// 環境タイプのフォーム
// ============================================================

export const environmentFormSchema = z.object({
  id: z
    .string()
    .min(1, "ID is required")
    .regex(/^[A-Z0-9_]+$/, "ID must be uppercase alphanumeric with underscores (例: FOREST)"),
  name: z.string().min(1, "Name is required"),
  description: z.string(),
  sensor_range_multiplier: numberField().gt(0, "Must be > 0").lte(1, "Must be ≤ 1"),
  ranged_accuracy_penalty: numberField().min(0, "Must be ≥ 0").max(1, "Must be ≤ 1"),
  ranged_penalty_ref_distance: numberField().gt(0, "Must be > 0"),
  default_obstacle_density: obstacleDensitySchema,
  default_terrain_grade: terrainGradeSchema,
  viewer_preset: viewerPresetSchema,
});

export type EnvironmentFormValues = z.infer<typeof environmentFormSchema>;

/** 新規作成の初期値。効果なし（宇宙と同じ）にする */
export function toEnvironmentFormValues(environment: MasterEnvironment | null): EnvironmentFormValues {
  if (!environment) {
    return {
      id: "",
      name: "",
      description: "",
      sensor_range_multiplier: 1.0,
      ranged_accuracy_penalty: 0,
      ranged_penalty_ref_distance: 400,
      default_obstacle_density: "MEDIUM",
      default_terrain_grade: "A",
      viewer_preset: "SPACE",
    };
  }
  return { ...environment };
}

// ============================================================
// 戦域のフォーム
// ============================================================

export const theaterFormSchema = z.object({
  id: z
    .string()
    .min(1, "ID is required")
    .regex(/^[a-z0-9_]+$/, "ID must be lowercase alphanumeric with underscores (snake_case)"),
  name: z.string().min(1, "Name is required"),
  environment_id: z.string().min(1, "環境タイプを選ぶ"),
  base_minovsky: numberField().min(0, "Must be ≥ 0").max(1, "Must be ≤ 1"),
  minovsky_variance: numberField().min(0, "Must be ≥ 0").max(0.5, "Must be ≤ 0.5"),
  /** 空文字は「環境タイプの既定値」 */
  obstacle_density: z.union([z.literal(""), obstacleDensitySchema]),
  hint: z.string(),
  description: z.string(),
  rotation_order: numberField().int("Must be an integer"),
  is_active: z.boolean(),
});

export type TheaterFormValues = z.infer<typeof theaterFormSchema>;

/** 新規作成の初期値。順番は既存の最後の戦域の後ろにする（初期データと同じ10刻み） */
export function toTheaterFormValues(
  theater: MasterTheater | null,
  existing: MasterTheater[] = []
): TheaterFormValues {
  if (!theater) {
    const lastOrder = existing.reduce((max, t) => Math.max(max, t.rotation_order), 0);
    return {
      id: "",
      name: "",
      environment_id: "",
      base_minovsky: 0.3,
      minovsky_variance: 0.1,
      obstacle_density: "",
      hint: "",
      description: "",
      rotation_order: lastOrder + 10,
      is_active: true,
    };
  }
  return { ...theater, obstacle_density: theater.obstacle_density ?? "" };
}

export function toTheaterPayload(values: TheaterFormValues): MasterTheater {
  return { ...values, obstacle_density: values.obstacle_density === "" ? null : values.obstacle_density };
}

/** backend と同じ `(rotation_order, id)` の順に並べる */
export function sortByRotation(theaters: MasterTheater[]): MasterTheater[] {
  return [...theaters].sort(
    (a, b) => a.rotation_order - b.rotation_order || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)
  );
}

/** 濃度の範囲（基準値 ± 揺らぎ幅、0〜1 にクランプ）を「20%〜50%」の形にする */
export function formatMinovskyRange(theater: Pick<MasterTheater, "base_minovsky" | "minovsky_variance">): string {
  const percent = (value: number) => Math.round(Math.min(Math.max(value, 0), 1) * 100);
  return `${percent(theater.base_minovsky - theater.minovsky_variance)}%〜${percent(
    theater.base_minovsky + theater.minovsky_variance
  )}%`;
}

const WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"];

/** 開催予定時刻（UTC）を JST の「10/2(金)」にする */
export function formatJstDate(iso: string): string {
  const jst = new Date(new Date(iso).getTime() + 9 * 60 * 60 * 1000);
  return `${jst.getUTCMonth() + 1}/${jst.getUTCDate()}(${WEEKDAYS[jst.getUTCDay()]})`;
}

// ============================================================
// 機体の地形適正
// ============================================================

/** 地形適正の入力値。空文字は「既定」（キーを保存せず、環境タイプの既定ランクを使う） */
export type TerrainGradeInput = TerrainGrade | "";

/** 環境タイプの地形適正を設定した新しいオブジェクトを返す。「既定」ならキーを消す */
export function setTerrainGrade(
  terrain: Record<string, string>,
  environmentId: string,
  grade: TerrainGradeInput
): Record<string, string> {
  const next = { ...terrain };
  if (grade === "") {
    delete next[environmentId];
  } else {
    next[environmentId] = grade;
  }
  return next;
}

/**
 * 環境タイプのマスターに無いキー（例: 旧来の GROUND）を返す。
 * 入力欄を出さず、保存時もそのまま残す。
 */
export function unmanagedTerrainKeys(
  environments: Pick<MasterEnvironment, "id">[],
  terrain: Record<string, string>
): string[] {
  const managed = new Set(environments.map((e) => e.id));
  return Object.keys(terrain)
    .filter((key) => !managed.has(key))
    .sort();
}

export const terrainAdaptabilitySchema = z.record(
  z.string(),
  z.string().refine((grade) => (TERRAIN_GRADES as readonly string[]).includes(grade), "S〜D で選ぶ")
);
