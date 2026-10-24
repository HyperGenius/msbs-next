"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { FieldErrors, FormProvider, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { Weapon } from "@/types/weapon";
import {
  FieldError,
  Input,
  MasterValueLabel,
  MobileSuitSpecSection,
  WeaponListSection,
  masterMobileSuitValue,
  sectionTitle,
  useMasterMobileSuit,
} from "@/components/admin/MobileSuitSpecFields";
import { NpcMobileSuitFormValues, npcMobileSuitSchema } from "@/components/admin/NpcMobileSuitEditForm";
import TerrainAdaptabilityFields from "@/components/admin/TerrainAdaptabilityFields";
import {
  diffValues,
  formValuesToSnapshot,
  formatChangeValue,
  snapshotToFormValues,
} from "@/lib/localSim/rosterEdit";

type Snapshot = Record<string, unknown>;
type Tab = "mobile_suit" | "weapons" | "terrain";

const TABS: [Tab, string][] = [
  ["mobile_suit", "機体"],
  ["weapons", "武装"],
  ["terrain", "地形適正"],
];

const APTITUDE_FIELDS = [
  ["mobile_suit.melee_aptitude", "格闘適性", "melee_aptitude"],
  ["mobile_suit.shooting_aptitude", "射撃適性", "shooting_aptitude"],
  ["mobile_suit.accuracy_bonus", "命中補正", "accuracy_bonus"],
  ["mobile_suit.evasion_bonus", "回避補正", "evasion_bonus"],
  ["mobile_suit.acceleration_bonus", "加速補正", "acceleration_bonus"],
  ["mobile_suit.turning_bonus", "旋回補正", "turning_bonus"],
] as const;

function tabHasError(tab: Tab, errors: FieldErrors<NpcMobileSuitFormValues>): boolean {
  if (tab === "terrain") return false;
  if (tab === "weapons") return !!errors.mobile_suit?.weapons;
  return Object.keys(errors.mobile_suit ?? {}).some((key) => key !== "weapons");
}

interface RosterEntryEditorProps {
  /** 編集を始める時点のスナップショット。複製した機体は複製元の値 */
  initial: Snapshot;
  /** 元のロスターの値。複製・追加した機体は null で、変更の強調をしない */
  original: Snapshot | null;
  idPrefix: string;
  /** 編集後のスナップショット。入力が不正なときは null */
  onChange: (snapshot: Snapshot | null) => void;
}

/** ロスターの機体1機分の編集欄。入力欄は NPC 機・エース機の編集と同じ部品を使う */
export default function RosterEntryEditor({ initial, original, idPrefix, onChange }: RosterEntryEditorProps) {
  "use no memo";
  const [tab, setTab] = useState<Tab>("mobile_suit");
  const [importedWeapons, setImportedWeapons] = useState<Weapon[]>([]);
  const [terrain, setTerrain] = useState<Record<string, string>>(
    (initial.terrain_adaptability as Record<string, string> | undefined) ?? {}
  );
  const initialValues = useMemo(() => snapshotToFormValues(initial), [initial]);
  const methods = useForm<NpcMobileSuitFormValues>({
    resolver: zodResolver(npcMobileSuitSchema),
    defaultValues: initialValues,
    mode: "onChange",
  });
  const {
    register,
    control,
    formState: { errors },
  } = methods;
  const values = useWatch({ control });
  const current = useWatch({ control, name: "mobile_suit" });
  const master = useMasterMobileSuit(current.master_mobile_suit_id);

  // 入力が変わるたびに検証し、通ったものだけ親へ渡す。値が元と同じなら元のスナップショットをそのまま返し、
  // フォームを通したことによる表記の違い（狙う部位配分の丸めなど）を変更として扱わない。
  const edited = useMemo(() => {
    const parsed = npcMobileSuitSchema.safeParse(values);
    if (!parsed.success) return null;
    const unchanged = JSON.stringify(parsed.data) === JSON.stringify(initialValues);
    const snapshot = unchanged ? initial : formValuesToSnapshot(parsed.data, initial, importedWeapons);
    return JSON.stringify(terrain) === JSON.stringify(initial.terrain_adaptability ?? {})
      ? snapshot
      : { ...snapshot, terrain_adaptability: terrain };
  }, [values, initial, initialValues, importedWeapons, terrain]);

  // 親が毎回新しい関数を渡しても、値が変わったときだけ通知する。
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  });
  useEffect(() => {
    onChangeRef.current(edited);
  }, [edited]);

  const changes = useMemo(() => (original && edited ? diffValues(original, edited) : []), [original, edited]);

  return (
    <FormProvider {...methods}>
      <div className="space-y-3 text-[#00ff41] font-mono">
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
                  <MasterValueLabel masterValue={masterMobileSuitValue(master, key)} currentValue={current[key]}>
                    {label}
                  </MasterValueLabel>
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
            idPrefix={idPrefix}
            onImportWeapon={(weapon) => setImportedWeapons((weapons) => [...weapons, weapon])}
          />
        </div>

        <div className={tab === "terrain" ? "" : "hidden"}>
          <TerrainAdaptabilityFields value={terrain} onChange={setTerrain} />
        </div>

        {original && (
          <div className="border border-[#ffb000]/40 bg-[#ffb000]/5 p-2 text-xs space-y-0.5">
            <p className="text-[#ffb000] font-bold">元のロスターからの変更（{changes.length} 件）</p>
            {changes.length === 0 && <p className="text-[#00ff41]/50">変更はありません</p>}
            {changes.map((change) => (
              <p key={change.path} className="break-all">
                <span className="text-[#ffb000]">{change.path}</span>: {formatChangeValue(change.before)} →{" "}
                {formatChangeValue(change.after)}
              </p>
            ))}
          </div>
        )}
      </div>
    </FormProvider>
  );
}
