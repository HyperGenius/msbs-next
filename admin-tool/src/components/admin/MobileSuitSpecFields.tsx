/* admin-tool/src/components/admin/MobileSuitSpecFields.tsx */
"use client";

import { Controller, useFieldArray, useFormContext, useWatch } from "react-hook-form";
import { z } from "zod";
import { MasterMobileSuit, MasterWeapon, NpcMobileSuit } from "@/types/admin";
import { Tactics, Weapon } from "@/types/weapon";
import { weaponSchema } from "@/components/admin/MobileSuitEditForm";
import MasterWeaponSelect from "@/components/admin/MasterWeaponSelect";
import { useAdminMobileSuits } from "@/hooks/useAdminMobileSuits";
import { useAdminWeapons } from "@/hooks/useAdminWeapons";

// ============================================================
// 定数
// ============================================================

export const TACTICS_PRIORITIES = ["CLOSEST", "WEAKEST", "RANDOM", "STRONGEST", "THREAT"] as const;
export const TACTICS_RANGES = ["MELEE", "RANGED", "BALANCED", "FLEE"] as const;
export const WEAPON_SWITCH_POLICIES = ["NEVER", "RACK_ONLY", "BALANCED", "AGGRESSIVE"] as const;
/** 未設定の機体の持ち替えポリシー（backend の DEFAULT_WEAPON_SWITCH_POLICY と同じ） */
export const DEFAULT_WEAPON_SWITCH_POLICY = "BALANCED";
/** Garage の TacticsSelector と同じ表示ラベル */
const WEAPON_SWITCH_POLICY_LABELS: Record<(typeof WEAPON_SWITCH_POLICIES)[number], string> = {
  NEVER: "NEVER - 持ち替えない",
  RACK_ONLY: "RACK_ONLY - 使用不能時のみ強制持ち替え",
  BALANCED: "BALANCED - おまかせ（期待効果で判断）",
  AGGRESSIVE: "AGGRESSIVE - 積極的に持ち替える",
};
/** 並び順は Garage の AimDistributionEditor の表示順と同じ */
export const PART_NAMES = ["HEAD", "TORSO", "RIGHT_ARM", "LEFT_ARM", "RIGHT_LEG", "LEFT_LEG"] as const;
type PartName = (typeof PART_NAMES)[number];
const PART_LABELS: Record<PartName, string> = {
  HEAD: "頭部",
  TORSO: "胴体",
  RIGHT_ARM: "右腕",
  LEFT_ARM: "左腕",
  RIGHT_LEG: "右脚",
  LEFT_LEG: "左脚",
};
/** backend の DEFAULT_AIM_DISTRIBUTION を % にした値 */
export const DEFAULT_AIM_DISTRIBUTION_PERCENT: Record<PartName, number> = {
  HEAD: 10,
  TORSO: 50,
  RIGHT_ARM: 10,
  LEFT_ARM: 10,
  RIGHT_LEG: 10,
  LEFT_LEG: 10,
};
/** 配分合計の許容誤差 (%)。backend の validate_aim_distribution と同じ */
const AIM_TOTAL_TOLERANCE_PERCENT = 1;
/** スロット数が未設定の機体の既定値（backend の MAX_WEAPON_SLOTS と同じ） */
export const DEFAULT_WEAPON_SLOT_COUNT = 2;

// ============================================================
// Zod バリデーションスキーマ
// ============================================================

const aimPercentSchema = z.number({ message: "Must be a number" }).nonnegative("Must be ≥ 0");

export function sumAimPercent(values: Partial<Record<PartName, number>>): number {
  const total = PART_NAMES.reduce((sum, p) => sum + (Number.isFinite(values[p]) ? values[p]! : 0), 0);
  // 小数の足し算の誤差を表示に出さないため
  return Math.round(total * 100) / 100;
}

/** 狙う部位配分（%）。API へは割合に直して送る */
export const aimDistributionSchema = z
  .object({
    HEAD: aimPercentSchema,
    TORSO: aimPercentSchema,
    RIGHT_ARM: aimPercentSchema,
    LEFT_ARM: aimPercentSchema,
    RIGHT_LEG: aimPercentSchema,
    LEFT_LEG: aimPercentSchema,
  })
  .superRefine((d, ctx) => {
    const total = sumAimPercent(d);
    if (Math.abs(total - 100) > AIM_TOTAL_TOLERANCE_PERCENT) {
      ctx.addIssue({ code: "custom", message: `Total must be 100% (current: ${total}%)` });
    }
  });

/**
 * NPC機・エース機の武装。機体マスターの武装と違い、狙う部位配分も編集する。
 * 武器マスターから作った武器は元の武器マスターIDを持つ。
 */
export const specWeaponSchema = weaponSchema.extend({
  aim_distribution: aimDistributionSchema,
  master_weapon_id: z.string().nullable(),
});

/** エース機・NPC機に共通する機体スペック */
export const mobileSuitSpecSchema = z.object({
  master_mobile_suit_id: z.string().nullable(),
  name: z.string().min(1, "Mobile suit name is required"),
  max_hp: z.number({ message: "Must be a number" }).int().positive("Must be > 0"),
  armor: z.number({ message: "Must be a number" }).int().nonnegative(),
  mobility: z.number({ message: "Must be a number" }).positive("Must be > 0"),
  sensor_range: z.number({ message: "Must be a number" }).positive(),
  beam_resistance: z.number({ message: "Must be a number" }).min(0).max(1),
  physical_resistance: z.number({ message: "Must be a number" }).min(0).max(1),
  max_en: z.number({ message: "Must be a number" }).int().nonnegative(),
  en_recovery: z.number({ message: "Must be a number" }).int().nonnegative(),
  tactics: z.object({
    priority: z.enum(TACTICS_PRIORITIES),
    range: z.enum(TACTICS_RANGES),
    weapon_switch_policy: z.enum(WEAPON_SWITCH_POLICIES),
  }),
  missing_parts: z.array(z.enum(PART_NAMES)),
  weapon_slot_count: z.number({ message: "Must be a number" }).int().min(1, "Must be ≥ 1"),
  weapons: z.array(specWeaponSchema).min(1, "At least one weapon is required"),
});

/**
 * 武装の本数がスロット数以下で、武器IDが重複しないことを検証する。
 * バトル中の弾数・クールダウンは武器IDをキーに持つため、同じIDの武器は状態を共有してしまう。
 * mobileSuitSpecSchema を extend した後に superRefine で使う（refine 済みの schema は extend できないため）。
 */
export function refineWeaponSlots(
  data: { weapon_slot_count: number; weapons: { id: string }[] },
  ctx: z.RefinementCtx
) {
  if (data.weapons.length > data.weapon_slot_count) {
    ctx.addIssue({
      code: "custom",
      message: `Number of weapons (${data.weapons.length}) exceeds weapon slot count (${data.weapon_slot_count})`,
      path: ["weapon_slot_count"],
    });
  }
  const seen = new Set<string>();
  data.weapons.forEach((w, index) => {
    if (seen.has(w.id)) {
      ctx.addIssue({ code: "custom", message: "Duplicate weapon ID", path: ["weapons", index, "id"] });
    }
    seen.add(w.id);
  });
}

export type MobileSuitSpecFormValues = z.infer<typeof mobileSuitSpecSchema>;
export type WeaponFormValues = MobileSuitSpecFormValues["weapons"][number];
export type AimDistributionFormValues = WeaponFormValues["aim_distribution"];

/** 共通セクションを載せるフォームの形。機体スペックは mobile_suit 配下に置く。 */
type SpecFormHost = { mobile_suit: MobileSuitSpecFormValues };

// ============================================================
// 変換ヘルパー
// ============================================================

export const defaultWeapon: WeaponFormValues = {
  id: "",
  name: "",
  power: 150,
  range: 400,
  accuracy: 80,
  type: "PHYSICAL",
  optimal_range: 300,
  decay_rate: 0.05,
  is_melee: false,
  en_cost: 0,
  cool_down_turn: 0,
  required_beam_generator_lv: 0,
  master_weapon_id: null,
  aim_distribution: { ...DEFAULT_AIM_DISTRIBUTION_PERCENT },
};

/**
 * 割合（0〜1）の配分を % のフォーム値に変換する。
 * 空の配分は既定値として扱う。バトルエンジンも空なら既定値を使うため。
 */
export function aimDistributionToFormValues(
  distribution: Record<string, number> | undefined
): AimDistributionFormValues {
  if (!distribution || Object.keys(distribution).length === 0) return { ...DEFAULT_AIM_DISTRIBUTION_PERCENT };
  // 0.1 * 100 のような誤差を小数第2位で丸める
  const toPercent = (ratio: number | undefined) => Math.round((ratio ?? 0) * 10000) / 100;
  return Object.fromEntries(PART_NAMES.map((p) => [p, toPercent(distribution[p])])) as AimDistributionFormValues;
}

export function aimDistributionToRatio(values: AimDistributionFormValues): Record<string, number> {
  return Object.fromEntries(PART_NAMES.map((p) => [p, values[p] / 100]));
}

export function weaponToFormValues(w: Weapon): WeaponFormValues {
  return {
    id: w.id,
    name: w.name,
    power: w.power,
    range: w.range,
    accuracy: w.accuracy,
    type: (w.type ?? "PHYSICAL") as "BEAM" | "PHYSICAL",
    optimal_range: w.optimal_range ?? 300,
    decay_rate: w.decay_rate ?? 0.05,
    is_melee: w.is_melee ?? false,
    max_ammo: w.max_ammo ?? null,
    en_cost: w.en_cost ?? 0,
    cool_down_turn: w.cool_down_turn ?? 0,
    required_beam_generator_lv: w.required_beam_generator_lv ?? 0,
    master_weapon_id: w.master_weapon_id ?? null,
    aim_distribution: aimDistributionToFormValues(w.aim_distribution),
  };
}

/** スロット番号の表示名。Garage（frontend/src/app/garage/constants.ts の getWeaponSlotLabel）と同じ対応 */
export function weaponSlotLabel(index: number): string {
  if (index === 0) return "右腕";
  if (index === 1) return "左腕";
  return `ラック${index - 1}`;
}

/** 既存の武器IDと重ならないよう、必要なら `{id}_2`、`{id}_3` … と接尾辞を付ける */
export function uniqueWeaponId(baseId: string, existingIds: string[]): string {
  const used = new Set(existingIds);
  if (!used.has(baseId)) return baseId;
  let n = 2;
  while (used.has(`${baseId}_${n}`)) n++;
  return `${baseId}_${n}`;
}

/** 武器マスターを機体の武装に変換する。フォーム外の項目も含めてスペックをコピーする */
export function masterWeaponToWeapon(master: MasterWeapon, existingIds: string[]): Weapon {
  return {
    ...master.weapon,
    id: uniqueWeaponId(master.id, existingIds),
    name: master.name,
    master_weapon_id: master.id,
  };
}

export function tacticsToFormValues(tactics: Partial<Tactics> | undefined): MobileSuitSpecFormValues["tactics"] {
  const priority = TACTICS_PRIORITIES.find((p) => p === tactics?.priority) ?? "CLOSEST";
  const range = TACTICS_RANGES.find((r) => r === tactics?.range) ?? "BALANCED";
  const weapon_switch_policy =
    WEAPON_SWITCH_POLICIES.find((p) => p === tactics?.weapon_switch_policy) ?? DEFAULT_WEAPON_SWITCH_POLICY;
  return { priority, range, weapon_switch_policy };
}

/** フォームの戦術に、フォームで扱わない既存のキーを足す。保存で消さないため */
export function mergeTactics(
  tactics: MobileSuitSpecFormValues["tactics"],
  source: Partial<Tactics> | undefined
): Tactics {
  return { ...source, ...tactics };
}

export function missingPartsToFormValues(parts: string[] | undefined): MobileSuitSpecFormValues["missing_parts"] {
  return PART_NAMES.filter((p) => parts?.includes(p));
}

/**
 * フォームの武装を API に送る Weapon に変換する。
 * フォームで扱わない項目（weapon_type / cooldown_sec / fire_arc_deg 等）は
 * 同じ武器IDの取り込み元から引き継ぐ。編集によって既定値へ巻き戻さないため。
 * sources に同じIDが複数あるときは後ろの要素を使う。
 */
export function mergeWeaponSources(weapons: WeaponFormValues[], sources: Weapon[]): Weapon[] {
  const byId = new Map(sources.map((w) => [w.id, w]));
  return weapons.map((w) => ({
    ...byId.get(w.id),
    ...w,
    aim_distribution: aimDistributionToRatio(w.aim_distribution),
  }));
}

/**
 * 機体マスターのスペックをフォーム値に変換する。
 * 機体マスターに無い項目（EN・戦術）は current の値を残す。
 * 機体マスターの武器は武器マスターに無い ID も持てる。masterWeaponIds にある ID だけ武器マスターIDとして記録する。
 */
export function masterToSpecValues(
  master: MasterMobileSuit,
  current: MobileSuitSpecFormValues,
  masterWeaponIds: ReadonlySet<string> = new Set()
): MobileSuitSpecFormValues {
  const specs = master.specs;
  return {
    ...current,
    master_mobile_suit_id: master.id,
    name: master.name,
    max_hp: specs.max_hp,
    armor: specs.armor,
    mobility: specs.mobility,
    sensor_range: specs.sensor_range,
    beam_resistance: specs.beam_resistance,
    physical_resistance: specs.physical_resistance,
    missing_parts: missingPartsToFormValues(specs.missing_parts),
    weapon_slot_count: master.weapon_slot_count,
    weapons: specs.weapons.map((w) => ({
      ...weaponToFormValues(w),
      master_weapon_id: masterWeaponIds.has(w.id) ? w.id : null,
    })),
  };
}

export function npcMobileSuitToSpecValues(ms: NpcMobileSuit): MobileSuitSpecFormValues {
  return {
    master_mobile_suit_id: ms.master_mobile_suit_id ?? null,
    name: ms.name,
    max_hp: ms.max_hp,
    armor: ms.armor,
    mobility: ms.mobility,
    sensor_range: ms.sensor_range,
    beam_resistance: ms.beam_resistance,
    physical_resistance: ms.physical_resistance,
    max_en: ms.max_en,
    en_recovery: ms.en_recovery,
    tactics: tacticsToFormValues(ms.tactics),
    missing_parts: missingPartsToFormValues(ms.missing_parts),
    weapon_slot_count: ms.weapon_slot_count,
    weapons: ms.weapons.map(weaponToFormValues),
  };
}

// ============================================================
// UI 部品
// ============================================================

export const inputCls =
  "w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41]";
export const sectionTitle =
  "text-xs font-bold text-[#ffb000] uppercase tracking-wider mb-2 border-b border-[#ffb000]/20 pb-1";

export function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="mt-0.5 text-xs text-red-400">{msg}</p>;
}

export function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="block text-xs text-[#ffb000]/80 mb-0.5">
      {children}
    </label>
  );
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputCls} disabled:opacity-50 ${className ?? ""}`} />;
}

// ============================================================
// マスター値の併記
// ============================================================

/** 機体マスターにも同じ項目があるもの。EN・戦術は機体マスターに無いため含めない */
export type MasterMobileSuitKey =
  | Exclude<keyof MasterMobileSuit["specs"], "weapons" | "missing_parts">
  | "weapon_slot_count";

/** 武器マスターにも同じ項目があり、フォームで編集できるもの */
type MasterWeaponKey = "power" | "range" | "accuracy" | "type" | "optimal_range" | "decay_rate" | "en_cost";

/** 機体マスターの項目の値。マスターが無い（未記録・削除済み）ときは undefined */
export function masterMobileSuitValue(
  master: MasterMobileSuit | undefined,
  key: MasterMobileSuitKey
): number | undefined {
  if (!master) return undefined;
  return key === "weapon_slot_count" ? master.weapon_slot_count : master.specs[key];
}

function masterWeaponValue(master: MasterWeapon | undefined, key: MasterWeaponKey): number | string | undefined {
  return master?.weapon[key];
}

/** 現在の機体マスターを ID で引く。一覧は SWR のキャッシュを共有する */
export function useMasterMobileSuit(id: string | null | undefined): MasterMobileSuit | undefined {
  const { mobileSuits } = useAdminMobileSuits();
  return id ? mobileSuits?.find((m) => m.id === id) : undefined;
}

/**
 * マスター値を「ラベル (値)」の形で併記するラベル。
 * 現在の値がマスター値と異なるときは色を変える。未入力（NaN）も異なるとみなす。
 * マスター値が undefined のときは通常の Label と同じ表示になる。
 */
export function MasterValueLabel({
  children,
  masterValue,
  currentValue,
}: {
  children: React.ReactNode;
  masterValue: number | string | undefined;
  currentValue: unknown;
}) {
  if (masterValue === undefined) return <Label>{children}</Label>;
  const differs = currentValue !== masterValue;
  return (
    <label
      className={`block text-xs mb-0.5 ${differs ? "text-[#00e5ff]" : "text-[#ffb000]/80"}`}
      title={differs ? "マスターの値と異なります" : undefined}
    >
      {children} ({masterValue})
    </label>
  );
}

/** 元になったマスター名の表示。マスターが無いときは何も表示しない */
export function MasterSourceBadge({ label, name }: { label: string; name: string | undefined }) {
  if (name === undefined) return null;
  return (
    <span className="ml-2 text-[10px] font-normal normal-case text-[#00e5ff]/80">
      {label}: {name}
    </span>
  );
}

// ============================================================
// フォームセクション（FormProvider 配下で使う）
// ============================================================

/** 機体スペック・戦術・欠損部位の入力欄 */
export function MobileSuitSpecSection({ namePlaceholder }: { namePlaceholder?: string }) {
  "use no memo";
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<SpecFormHost>();
  const msErrors = errors.mobile_suit;
  const current = useWatch({ control, name: "mobile_suit" });
  const master = useMasterMobileSuit(current.master_mobile_suit_id);

  return (
    <>
      <div>
        <p className={sectionTitle}>
          スペック
          <MasterSourceBadge label="機体マスター" name={master?.name} />
        </p>
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-3">
            <Label>機体名</Label>
            <Input {...register("mobile_suit.name")} placeholder={namePlaceholder} />
            <FieldError msg={msErrors?.name?.message} />
          </div>
          {(
            [
              ["max_hp", "最大 HP", "1"],
              ["armor", "装甲", "1"],
              ["mobility", "機動性", "0.01"],
              ["sensor_range", "索敵範囲", "1"],
              ["beam_resistance", "ビーム耐性 (0-1)", "0.01"],
              ["physical_resistance", "実弾耐性 (0-1)", "0.01"],
              ["max_en", "最大 EN", "1"],
              ["en_recovery", "EN 回復量", "1"],
              ["weapon_slot_count", "武器スロット数", "1"],
            ] as const
          ).map(([key, label, step]) => (
            <div key={key}>
              <MasterValueLabel
                masterValue={key === "max_en" || key === "en_recovery" ? undefined : masterMobileSuitValue(master, key)}
                currentValue={current[key]}
              >
                {label}
              </MasterValueLabel>
              <Input type="number" step={step} {...register(`mobile_suit.${key}`, { valueAsNumber: true })} />
              <FieldError msg={msErrors?.[key]?.message} />
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className={sectionTitle}>戦術</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>ターゲット優先度</Label>
            <select {...register("mobile_suit.tactics.priority")} className={inputCls}>
              {TACTICS_PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>交戦距離</Label>
            <select {...register("mobile_suit.tactics.range")} className={inputCls}>
              {TACTICS_RANGES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div className="col-span-2">
            <Label>武装持ち替え</Label>
            <select {...register("mobile_suit.tactics.weapon_switch_policy")} className={inputCls}>
              {WEAPON_SWITCH_POLICIES.map((p) => (
                <option key={p} value={p}>
                  {WEAPON_SWITCH_POLICY_LABELS[p]}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div>
        <p className={sectionTitle}>欠損部位</p>
        <Controller
          control={control}
          name="mobile_suit.missing_parts"
          render={({ field }) => (
            <div className="grid grid-cols-3 gap-2">
              {PART_NAMES.map((part) => (
                <label key={part} className="flex items-center gap-2 text-xs text-[#00ff41]/80">
                  <input
                    type="checkbox"
                    className="accent-[#00ff41]"
                    checked={field.value.includes(part)}
                    onChange={(e) =>
                      field.onChange(
                        e.target.checked ? [...field.value, part] : field.value.filter((p) => p !== part)
                      )
                    }
                  />
                  {part}
                </label>
              ))}
            </div>
          )}
        />
      </div>
    </>
  );
}

interface WeaponListSectionProps {
  /** 同一ページ内でチェックボックスの id を重複させないために使う */
  idPrefix: string;
  /** 武器マスターから追加した武器。送信時に mergeWeaponSources() の取り込み元に加える */
  onImportWeapon: (weapon: Weapon) => void;
}

/** 武装リストの入力欄 */
export function WeaponListSection({ idPrefix, onImportWeapon }: WeaponListSectionProps) {
  "use no memo";
  const {
    register,
    control,
    getValues,
    formState: { errors },
  } = useFormContext<SpecFormHost>();
  const weaponArray = useFieldArray({ control, name: "mobile_suit.weapons" });
  const weaponErrors = errors.mobile_suit?.weapons;
  const slotCount = useWatch({ control, name: "mobile_suit.weapon_slot_count" });
  const currentWeapons = useWatch({ control, name: "mobile_suit.weapons" });
  const { weapons: masterWeapons } = useAdminWeapons();
  const isFull = Number.isFinite(slotCount) && weaponArray.fields.length >= slotCount;

  function handleImportWeapon(master: MasterWeapon) {
    const existingIds = getValues("mobile_suit.weapons").map((w) => w.id);
    const weapon = masterWeaponToWeapon(master, existingIds);
    weaponArray.append(weaponToFormValues(weapon));
    onImportWeapon(weapon);
  }

  return (
    <>
      <div className="flex items-center justify-between mb-2">
        <p className={`${sectionTitle} flex-1`}>
          武装 ({weaponArray.fields.length} / {Number.isFinite(slotCount) ? slotCount : "-"})
        </p>
        <button
          type="button"
          disabled={isFull}
          onClick={() => weaponArray.append({ ...defaultWeapon })}
          className="text-xs text-[#00ff41] border border-[#00ff41]/40 px-2 py-0.5 hover:border-[#00ff41] ml-4 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          + 追加
        </button>
      </div>
      <div className="mb-3">
        <MasterWeaponSelect buttonLabel="追加" onApply={handleImportWeapon} disabled={isFull} />
        <p className="mt-1 text-xs text-[#00ff41]/40">
          {isFull
            ? "※ 武器スロットが埋まっています。機体タブでスロット数を増やすと追加できます"
            : "※ 武器マスターのスペックをコピーして末尾に追加します。同じ武器IDがある場合は接尾辞を付けます"}
        </p>
      </div>
      {(weaponErrors?.message || weaponErrors?.root?.message) && (
        <p className="text-xs text-red-400 mb-2">{weaponErrors.message ?? weaponErrors.root?.message}</p>
      )}
      <div className="space-y-4">
        {weaponArray.fields.map((field, index) => {
          const wErrors = weaponErrors?.[index];
          const current = currentWeapons[index];
          const masterId = current?.master_weapon_id;
          const master = masterId ? masterWeapons?.find((w) => w.id === masterId) : undefined;
          const masterLabel = (key: MasterWeaponKey, label: string) => (
            <MasterValueLabel masterValue={masterWeaponValue(master, key)} currentValue={current?.[key]}>
              {label}
            </MasterValueLabel>
          );
          return (
            <div key={field.id} className="border border-[#00ff41]/20 p-3 bg-[#080808]">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-[#ffb000]/60">
                  {weaponSlotLabel(index)}
                  <MasterSourceBadge label="武器マスター" name={master?.name} />
                </span>
                {weaponArray.fields.length > 1 && (
                  <button
                    type="button"
                    onClick={() => weaponArray.remove(index)}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    削除
                  </button>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <Label>ID (snake_case)</Label>
                  <Input {...register(`mobile_suit.weapons.${index}.id`)} placeholder="beam_rifle" />
                  <FieldError msg={wErrors?.id?.message} />
                </div>
                <div className="col-span-2">
                  <Label>名前</Label>
                  <Input {...register(`mobile_suit.weapons.${index}.name`)} placeholder="Beam Rifle" />
                  <FieldError msg={wErrors?.name?.message} />
                </div>
                <div>
                  {masterLabel("power", "威力")}
                  <Input type="number" {...register(`mobile_suit.weapons.${index}.power`, { valueAsNumber: true })} />
                  <FieldError msg={wErrors?.power?.message} />
                </div>
                <div>
                  {masterLabel("range", "射程")}
                  <Input type="number" {...register(`mobile_suit.weapons.${index}.range`, { valueAsNumber: true })} />
                  <FieldError msg={wErrors?.range?.message} />
                </div>
                <div>
                  {masterLabel("accuracy", "命中率 (%)")}
                  <Input
                    type="number"
                    {...register(`mobile_suit.weapons.${index}.accuracy`, { valueAsNumber: true })}
                  />
                  <FieldError msg={wErrors?.accuracy?.message} />
                </div>
                <div>
                  {masterLabel("type", "種別")}
                  <select {...register(`mobile_suit.weapons.${index}.type`)} className={inputCls}>
                    <option value="PHYSICAL">PHYSICAL</option>
                    <option value="BEAM">BEAM</option>
                  </select>
                </div>
                <div>
                  {masterLabel("optimal_range", "最適射程")}
                  <Input
                    type="number"
                    step="0.1"
                    {...register(`mobile_suit.weapons.${index}.optimal_range`, { valueAsNumber: true })}
                  />
                </div>
                <div>
                  {masterLabel("decay_rate", "減衰係数")}
                  <Input
                    type="number"
                    step="0.01"
                    {...register(`mobile_suit.weapons.${index}.decay_rate`, { valueAsNumber: true })}
                  />
                </div>
                <div>
                  {masterLabel("en_cost", "消費 EN")}
                  <Input
                    type="number"
                    min={0}
                    {...register(`mobile_suit.weapons.${index}.en_cost`, { valueAsNumber: true })}
                  />
                  <FieldError msg={wErrors?.en_cost?.message} />
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <Controller
                    control={control}
                    name={`mobile_suit.weapons.${index}.is_melee`}
                    render={({ field: f }) => (
                      <input
                        type="checkbox"
                        id={`${idPrefix}_is_melee_${index}`}
                        checked={f.value}
                        onChange={f.onChange}
                        className="accent-[#00ff41]"
                      />
                    )}
                  />
                  <label htmlFor={`${idPrefix}_is_melee_${index}`} className="text-xs text-[#00ff41]/80">
                    近接武器
                  </label>
                </div>
              </div>
              <AimDistributionFields index={index} />
            </div>
          );
        })}
      </div>
    </>
  );
}

/** 1 本の武器の狙う部位配分の入力欄。既定では閉じておく */
function AimDistributionFields({ index }: { index: number }) {
  "use no memo";
  const {
    register,
    control,
    setValue,
    formState: { errors },
  } = useFormContext<SpecFormHost>();
  const name = `mobile_suit.weapons.${index}.aim_distribution` as const;
  const values = useWatch({ control, name });
  const total = sumAimPercent(values ?? {});
  const isValidTotal = Math.abs(total - 100) <= AIM_TOTAL_TOLERANCE_PERCENT;
  const aimErrors = errors.mobile_suit?.weapons?.[index]?.aim_distribution;

  return (
    <details className="mt-3 border-t border-[#00ff41]/10 pt-2">
      <summary className="cursor-pointer text-xs text-[#ffb000]/80">
        狙う部位配分
        <span className={`ml-2 font-mono ${isValidTotal ? "text-[#00ff41]/70" : "text-red-400"}`}>
          合計: {total}%
        </span>
        {aimErrors && <span className="ml-1 text-red-400">!</span>}
      </summary>
      <div className="grid grid-cols-3 gap-2 mt-2">
        {PART_NAMES.map((part) => (
          <div key={part}>
            <Label>{PART_LABELS[part]} (%)</Label>
            {/* min / step を付けない。閉じた欄でブラウザの検証に掛かると、エラーを表示できず送信が止まるため */}
            <Input type="number" step="any" {...register(`${name}.${part}`, { valueAsNumber: true })} />
            <FieldError msg={aimErrors?.[part]?.message} />
          </div>
        ))}
      </div>
      <FieldError msg={aimErrors?.message ?? aimErrors?.root?.message} />
      <div className="flex items-center justify-between mt-2">
        <p className="text-xs text-[#00ff41]/40">※ 合計 100% にしてください（許容誤差 ±1%）</p>
        <button
          type="button"
          onClick={() =>
            setValue(name, { ...DEFAULT_AIM_DISTRIBUTION_PERCENT }, { shouldDirty: true, shouldValidate: true })
          }
          className="text-xs text-[#00ff41]/50 hover:text-[#00ff41] underline"
        >
          既定値に戻す
        </button>
      </div>
    </details>
  );
}
