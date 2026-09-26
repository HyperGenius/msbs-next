/* admin-tool/src/components/admin/NpcMobileSuitEditForm.tsx */
"use client";

import { useEffect, useState } from "react";
import { FieldErrors, FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { NpcMobileSuit, NpcMobileSuitUpdate } from "@/types/admin";
import { Weapon } from "@/types/weapon";
import {
  FieldError,
  Input,
  Label,
  MobileSuitSpecSection,
  WeaponListSection,
  mergeWeaponSources,
  mobileSuitSpecSchema,
  npcMobileSuitToSpecValues,
  refineWeaponSlots,
  sectionTitle,
} from "@/components/admin/MobileSuitSpecFields";

// ============================================================
// Zod バリデーションスキーマ
// ============================================================

export const npcMobileSuitSchema = z.object({
  mobile_suit: mobileSuitSpecSchema
    .extend({
      melee_aptitude: z.number({ message: "Must be a number" }).positive("Must be > 0"),
      shooting_aptitude: z.number({ message: "Must be a number" }).positive("Must be > 0"),
      accuracy_bonus: z.number({ message: "Must be a number" }),
      evasion_bonus: z.number({ message: "Must be a number" }),
      acceleration_bonus: z.number({ message: "Must be a number" }).positive("Must be > 0"),
      turning_bonus: z.number({ message: "Must be a number" }).positive("Must be > 0"),
    })
    .superRefine(refineWeaponSlots),
});

export type NpcMobileSuitFormValues = z.infer<typeof npcMobileSuitSchema>;

// ============================================================
// 変換ヘルパー
// ============================================================

export function toNpcMobileSuitFormValues(ms: NpcMobileSuit): NpcMobileSuitFormValues {
  return {
    mobile_suit: {
      ...npcMobileSuitToSpecValues(ms),
      melee_aptitude: ms.melee_aptitude,
      shooting_aptitude: ms.shooting_aptitude,
      accuracy_bonus: ms.accuracy_bonus,
      evasion_bonus: ms.evasion_bonus,
      acceleration_bonus: ms.acceleration_bonus,
      turning_bonus: ms.turning_bonus,
    },
  };
}

/**
 * フォーム値を API リクエストに変換する。
 * 武装の取り込み元は既存機体の武装と、武器マスターから追加した武装の2つ。
 */
export function toNpcMobileSuitPayload(
  values: NpcMobileSuitFormValues,
  original: NpcMobileSuit,
  importedWeapons: Weapon[] = []
): NpcMobileSuitUpdate {
  return {
    ...values.mobile_suit,
    weapons: mergeWeaponSources(values.mobile_suit.weapons, [...original.weapons, ...importedWeapons]),
  };
}

// ============================================================
// UI
// ============================================================

type Tab = "mobile_suit" | "weapons";

const TABS: [Tab, string][] = [
  ["mobile_suit", "機体"],
  ["weapons", "武装"],
];

const APTITUDE_FIELDS = [
  ["mobile_suit.melee_aptitude", "格闘適性", "melee_aptitude"],
  ["mobile_suit.shooting_aptitude", "射撃適性", "shooting_aptitude"],
  ["mobile_suit.accuracy_bonus", "命中補正", "accuracy_bonus"],
  ["mobile_suit.evasion_bonus", "回避補正", "evasion_bonus"],
  ["mobile_suit.acceleration_bonus", "加速補正", "acceleration_bonus"],
  ["mobile_suit.turning_bonus", "旋回補正", "turning_bonus"],
] as const;

/** 非表示タブのエラーを見落とさないよう、タブごとにエラー有無を判定する */
function tabHasError(tab: Tab, errors: FieldErrors<NpcMobileSuitFormValues>): boolean {
  const msErrors = errors.mobile_suit ?? {};
  if (tab === "weapons") return !!errors.mobile_suit?.weapons;
  return Object.keys(msErrors).some((key) => key !== "weapons");
}

interface NpcMobileSuitEditFormProps {
  mobileSuit: NpcMobileSuit;
  onSubmit: (msId: string, payload: NpcMobileSuitUpdate) => Promise<void>;
  onClose: () => void;
}

export default function NpcMobileSuitEditForm({ mobileSuit, onSubmit, onClose }: NpcMobileSuitEditFormProps) {
  "use no memo";
  const [tab, setTab] = useState<Tab>("mobile_suit");
  // 追加した武装は、追加した時点の編集対象に紐付ける。
  // mobileSuit が変わったら（保存後の再取得など）空として扱い、次の保存に混ぜない。
  // ID ではなく参照で比べるのは、下の useEffect の reset() と同じ契機にそろえるため。
  // reset() で追加した武装もフォームから消えるので、取り込み元だけが残ることはない。
  const [imported, setImported] = useState<{ source: NpcMobileSuit; weapons: Weapon[] }>({
    source: mobileSuit,
    weapons: [],
  });
  const importedWeapons = imported.source === mobileSuit ? imported.weapons : [];
  const methods = useForm<NpcMobileSuitFormValues>({
    resolver: zodResolver(npcMobileSuitSchema),
    defaultValues: toNpcMobileSuitFormValues(mobileSuit),
  });
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty, isSubmitting },
  } = methods;

  useEffect(() => {
    reset(toNpcMobileSuitFormValues(mobileSuit));
  }, [mobileSuit, reset]);

  function handleInvalid(invalidErrors: FieldErrors<NpcMobileSuitFormValues>) {
    const firstErrorTab = TABS.find(([key]) => tabHasError(key, invalidErrors));
    if (firstErrorTab) setTab(firstErrorTab[0]);
  }

  async function submit(values: NpcMobileSuitFormValues) {
    await onSubmit(mobileSuit.id, toNpcMobileSuitPayload(values, mobileSuit, importedWeapons));
  }

  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(submit, handleInvalid)} className="space-y-4 text-[#00ff41] font-mono">
        <div className="flex border-b border-[#00ff41]/20">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`px-3 py-1.5 text-xs font-bold border-b-2 -mb-px transition-colors ${
                tab === key
                  ? "border-[#ffb000] text-[#ffb000]"
                  : "border-transparent text-[#00ff41]/60 hover:text-[#00ff41]"
              }`}
            >
              {label}
              {tabHasError(key, errors) && <span className="ml-1 text-red-400">!</span>}
            </button>
          ))}
        </div>

        <div className={tab === "mobile_suit" ? "space-y-4" : "hidden"}>
          <MobileSuitSpecSection />
          <div>
            <p className={sectionTitle}>適性・補正</p>
            <div className="grid grid-cols-3 gap-3">
              {APTITUDE_FIELDS.map(([name, label, key]) => (
                <div key={name}>
                  <Label>{label}</Label>
                  <Input type="number" step="0.01" {...register(name, { valueAsNumber: true })} />
                  <FieldError msg={errors.mobile_suit?.[key]?.message} />
                </div>
              ))}
            </div>
          </div>
          <p className="text-xs text-[#00ff41]/40">※ 最大 HP を変更すると現在 HP も最大 HP に揃えます</p>
        </div>

        <div className={tab === "weapons" ? "" : "hidden"}>
          <WeaponListSection
            idPrefix={`npc_${mobileSuit.id}`}
            onImportWeapon={(weapon) =>
              setImported({ source: mobileSuit, weapons: [...importedWeapons, weapon] })
            }
          />
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting || !isDirty}
            className="flex-1 bg-[#00ff41]/10 border border-[#00ff41]/60 text-[#00ff41] py-1.5 text-xs font-bold hover:bg-[#00ff41]/20 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "保存中..." : "この機体を保存"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="flex-1 border border-[#00ff41]/30 text-[#00ff41]/60 py-1.5 text-xs hover:border-[#00ff41]/60"
          >
            閉じる
          </button>
        </div>
      </form>
    </FormProvider>
  );
}
