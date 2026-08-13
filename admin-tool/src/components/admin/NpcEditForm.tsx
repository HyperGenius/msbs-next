/* admin-tool/src/components/admin/NpcEditForm.tsx */
"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { NpcMobileSuit, NpcPilotDetail, NpcPersonality } from "@/types/admin";

// ============================================================
// Zod バリデーションスキーマ
// ============================================================

export const npcPilotSchema = z.object({
  npc_personality: z.enum(["AGGRESSIVE", "CAUTIOUS", "SNIPER"]),
  level: z.number({ message: "Must be a number" }).int().min(1, "Must be ≥ 1"),
  exp: z.number({ message: "Must be a number" }).int().nonnegative(),
  credits: z.number({ message: "Must be a number" }).int().nonnegative(),
  skill_points: z.number({ message: "Must be a number" }).int().nonnegative(),
  status_points: z.number({ message: "Must be a number" }).int().nonnegative(),
  sht: z.number({ message: "Must be a number" }).int().nonnegative(),
  mel: z.number({ message: "Must be a number" }).int().nonnegative(),
  intel: z.number({ message: "Must be a number" }).int().nonnegative(),
  ref: z.number({ message: "Must be a number" }).int().nonnegative(),
  tou: z.number({ message: "Must be a number" }).int().nonnegative(),
  luk: z.number({ message: "Must be a number" }).int().nonnegative(),
  awq: z.number({ message: "Must be a number" }).int().nonnegative(),
});

export type NpcPilotFormValues = z.infer<typeof npcPilotSchema>;

function toFormValues(npc: NpcPilotDetail): NpcPilotFormValues {
  return {
    npc_personality: (npc.npc_personality ?? "AGGRESSIVE") as NpcPersonality,
    level: npc.level,
    exp: npc.exp,
    credits: npc.credits,
    skill_points: npc.skill_points,
    status_points: npc.status_points,
    sht: npc.sht,
    mel: npc.mel,
    intel: npc.intel,
    ref: npc.ref,
    tou: npc.tou,
    luk: npc.luk,
    awq: npc.awq,
  };
}

// ============================================================
// UIヘルパー
// ============================================================

function Label({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs text-[#00ff41]/60 mb-1">{children}</label>;
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-xs text-red-400 mt-1">{message}</p>;
}

const inputClass =
  "w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1.5 text-sm font-mono focus:outline-none focus:border-[#00ff41]";

// ============================================================
// コンポーネント
// ============================================================

interface NpcEditFormProps {
  npc: NpcPilotDetail;
  onSubmitPilot: (values: NpcPilotFormValues) => Promise<void>;
  onSubmitMobileSuit: (msId: string, payload: { name?: string; max_hp?: number; armor?: number; mobility?: number }) => Promise<void>;
  isSubmitting?: boolean;
}

export default function NpcEditForm({ npc, onSubmitPilot, onSubmitMobileSuit, isSubmitting }: NpcEditFormProps) {
  "use no memo";
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<NpcPilotFormValues>({
    resolver: zodResolver(npcPilotSchema),
    defaultValues: toFormValues(npc),
  });

  useEffect(() => {
    reset(toFormValues(npc));
  }, [npc, reset]);

  const numberField = (key: keyof NpcPilotFormValues) => register(key, { valueAsNumber: true });

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit(onSubmitPilot)} className="space-y-4">
        <div>
          <Label>性格</Label>
          <select {...register("npc_personality")} className={inputClass}>
            <option value="AGGRESSIVE">AGGRESSIVE</option>
            <option value="CAUTIOUS">CAUTIOUS</option>
            <option value="SNIPER">SNIPER</option>
          </select>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label>レベル</Label>
            <input type="number" {...numberField("level")} className={inputClass} />
            <FieldError message={errors.level?.message} />
          </div>
          <div>
            <Label>EXP</Label>
            <input type="number" {...numberField("exp")} className={inputClass} />
            <FieldError message={errors.exp?.message} />
          </div>
          <div>
            <Label>クレジット</Label>
            <input type="number" {...numberField("credits")} className={inputClass} />
            <FieldError message={errors.credits?.message} />
          </div>
          <div>
            <Label>スキルポイント</Label>
            <input type="number" {...numberField("skill_points")} className={inputClass} />
            <FieldError message={errors.skill_points?.message} />
          </div>
          <div>
            <Label>ステータスポイント</Label>
            <input type="number" {...numberField("status_points")} className={inputClass} />
            <FieldError message={errors.status_points?.message} />
          </div>
        </div>

        <div>
          <p className="text-xs text-[#ffb000]/80 mb-2 font-bold">ステータス</p>
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
            {(["sht", "mel", "intel", "ref", "tou", "luk", "awq"] as const).map((key) => (
              <div key={key}>
                <Label>{key.toUpperCase()}</Label>
                <input type="number" {...numberField(key)} className={inputClass} />
                <FieldError message={errors[key]?.message} />
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={isSubmitting || !isDirty}
            className="flex-1 bg-[#00ff41]/10 border border-[#00ff41]/60 text-[#00ff41] py-2 text-sm font-bold hover:bg-[#00ff41]/20 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "保存中..." : "保存"}
          </button>
        </div>
      </form>

      <div className="border-t border-[#00ff41]/20 pt-4">
        <p className="text-xs text-[#ffb000]/80 mb-3 font-bold">所属機体（{npc.mobile_suits.length}）</p>
        <div className="space-y-3">
          {npc.mobile_suits.map((ms) => (
            <MobileSuitInlineEditor key={ms.id} mobileSuit={ms} onSubmit={onSubmitMobileSuit} />
          ))}
          {npc.mobile_suits.length === 0 && (
            <p className="text-xs text-[#00ff41]/40 text-center py-4">所属機体がありません</p>
          )}
        </div>
      </div>
    </div>
  );
}

function MobileSuitInlineEditor({
  mobileSuit,
  onSubmit,
}: {
  mobileSuit: NpcMobileSuit;
  onSubmit: (msId: string, payload: { name?: string; max_hp?: number; armor?: number; mobility?: number }) => Promise<void>;
}) {
  const [maxHp, setMaxHp] = useState(mobileSuit.max_hp);
  const [armor, setArmor] = useState(mobileSuit.armor);
  const [mobility, setMobility] = useState(mobileSuit.mobility);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setMaxHp(mobileSuit.max_hp);
    setArmor(mobileSuit.armor);
    setMobility(mobileSuit.mobility);
  }, [mobileSuit]);

  const dirty = maxHp !== mobileSuit.max_hp || armor !== mobileSuit.armor || mobility !== mobileSuit.mobility;

  async function handleSave() {
    setSaving(true);
    try {
      await onSubmit(mobileSuit.id, { max_hp: maxHp, armor, mobility });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="border border-[#00ff41]/20 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-bold text-[#00ff41]">
          {mobileSuit.name}
          {mobileSuit.is_ace && (
            <span className="ml-2 px-1.5 py-0.5 text-[10px] font-bold bg-[#ffb000]/20 text-[#ffb000] border border-[#ffb000]/50">
              ACE
            </span>
          )}
        </p>
        <span className="text-xs text-[#00ff41]/50">
          HP {mobileSuit.current_hp}/{mobileSuit.max_hp}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <Label>最大HP</Label>
          <input
            type="number"
            value={maxHp}
            onChange={(e) => setMaxHp(Number(e.target.value))}
            className={inputClass}
          />
        </div>
        <div>
          <Label>装甲</Label>
          <input
            type="number"
            value={armor}
            onChange={(e) => setArmor(Number(e.target.value))}
            className={inputClass}
          />
        </div>
        <div>
          <Label>機動性</Label>
          <input
            type="number"
            step="0.1"
            value={mobility}
            onChange={(e) => setMobility(Number(e.target.value))}
            className={inputClass}
          />
        </div>
      </div>
      <button
        onClick={handleSave}
        disabled={!dirty || saving}
        className="w-full border border-[#00ff41]/40 text-[#00ff41]/80 py-1.5 text-xs font-bold hover:bg-[#00ff41]/10 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {saving ? "保存中..." : "この機体を保存"}
      </button>
    </div>
  );
}
