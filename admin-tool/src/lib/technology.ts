import { z } from "zod";
import { MasterTechnology, TechRequirement } from "@/types/admin";

// ============================================================
// 閾値
// ============================================================

/**
 * 閾値の検証。backend の validate_level_thresholds と同じ規則。
 * 1要素以上で、正の整数の狭義単調増加であること。
 *
 * @returns エラーの文言。正しければ null
 */
export function thresholdsError(thresholds: number[]): string | null {
  if (thresholds.length === 0) return "1つ以上入力する";
  if (thresholds.some((t) => !Number.isInteger(t))) return "整数で入力する";
  if (thresholds[0] < 1) return "1以上で入力する";
  if (thresholds.some((t, i) => i > 0 && thresholds[i - 1] >= t)) return "小さい順に、同じ値を含めずに入力する";
  return null;
}

/** 「3, 8, 15」のような入力を数値の配列にする。空の要素は無視する */
export function parseThresholds(text: string): number[] {
  return text
    .split(/[,、\s]+/)
    .filter((part) => part !== "")
    .map(Number);
}

export function formatThresholds(thresholds: number[]): string {
  return thresholds.join(", ");
}

// ============================================================
// 技術マスターのフォーム
// ============================================================

export const technologyFormSchema = z.object({
  id: z
    .string()
    .min(1, "ID is required")
    .regex(/^[a-z0-9_]+$/, "ID must be lowercase alphanumeric with underscores (snake_case)"),
  name: z.string().min(1, "Name is required"),
  description: z.string(),
  level_thresholds: z.string().superRefine((text, ctx) => {
    const error = thresholdsError(parseThresholds(text));
    if (error) ctx.addIssue({ code: "custom", message: error });
  }),
  overflow_credit_value: z
    .number({ message: "Must be a number" })
    .int("Must be an integer")
    .nonnegative("Must be ≥ 0"),
});

export type TechnologyFormValues = z.infer<typeof technologyFormSchema>;

// 換金額の初期値。backend/data/master/technologies.json の値に合わせる。
export const DEFAULT_OVERFLOW_CREDIT_VALUE = 500;

export function toTechnologyFormValues(tech: MasterTechnology | null): TechnologyFormValues {
  if (!tech) {
    return {
      id: "",
      name: "",
      description: "",
      level_thresholds: "3, 8, 15",
      overflow_credit_value: DEFAULT_OVERFLOW_CREDIT_VALUE,
    };
  }
  return { ...tech, level_thresholds: formatThresholds(tech.level_thresholds) };
}

export function toTechnologyPayload(values: TechnologyFormValues): MasterTechnology {
  return { ...values, level_thresholds: parseThresholds(values.level_thresholds) };
}

// ============================================================
// 設計図の必要な技術Lv
// ============================================================

export const techRequirementsSchema = z
  .array(
    z.object({
      tech_id: z.string().min(1, "技術を選ぶ"),
      required_lv: z.number({ message: "Must be a number" }).int("Must be an integer").min(1, "Must be ≥ 1"),
    })
  )
  .superRefine((requirements, ctx) => {
    const seen = new Set<string>();
    requirements.forEach((requirement, index) => {
      if (seen.has(requirement.tech_id)) {
        ctx.addIssue({ code: "custom", path: [index, "tech_id"], message: "同じ技術が2つある" });
      }
      seen.add(requirement.tech_id);
    });
  });

/** 技術の最大Lv（閾値の要素数） */
export function maxLevelOf(tech: Pick<MasterTechnology, "level_thresholds">): number {
  return tech.level_thresholds.length;
}

/** 行を追加するときの初期値。まだ使っていない最初の技術を Lv1 で返す。全て使用済みなら null */
export function newTechRequirement(
  technologies: MasterTechnology[],
  current: TechRequirement[]
): TechRequirement | null {
  const used = new Set(current.map((r) => r.tech_id));
  const tech = technologies.find((t) => !used.has(t.id));
  return tech ? { tech_id: tech.id, required_lv: 1 } : null;
}

/** 必要な技術Lvの表示（例: 「サイコミュ技術 Lv2」）。技術マスターに無ければIDで表示する */
export function formatTechRequirement(
  requirement: TechRequirement,
  technologies: MasterTechnology[] | undefined
): string {
  const name = technologies?.find((t) => t.id === requirement.tech_id)?.name ?? requirement.tech_id;
  return `${name} Lv${requirement.required_lv}`;
}

/** react-hook-form のネストしたエラーから、最初に見つかった文言を返す */
export function firstErrorMessage(error: unknown): string | undefined {
  if (!error || typeof error !== "object") return undefined;
  const record = error as Record<string, unknown>;
  if (typeof record.message === "string" && record.message) return record.message;
  for (const value of Object.values(record)) {
    if (value && typeof value === "object") {
      const message = firstErrorMessage(value);
      if (message) return message;
    }
  }
  return undefined;
}
