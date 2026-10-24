"use client";

import { useState } from "react";
import type { LocalSimMissionMaster, LocalSimMissionUnit } from "@/types/localSim";
import { NumberField, SelectField, TextField } from "@/components/admin/RosterFields";

/** backend の VALID_UNIT_ROLES（app/engine/constants.py） */
const ROLE_OPTIONS = [
  { value: "", label: "（なし）" },
  ...["VANGUARD", "SUPPORT", "SNIPER", "COMMANDER", "WITHDRAW"].map((role) => ({ value: role, label: role })),
];

type Side = "allies" | "enemies";

interface UnitItem {
  key: string;
  unit: LocalSimMissionUnit;
  /** 元のロスターの値。複製した機体は null で、変更の強調をしない */
  original: LocalSimMissionUnit | null;
}

/** 編集後の作戦マスターで、友軍・敵機・作戦目標の必要数が数として正しいか確かめる */
export function missionMasterError(master: LocalSimMissionMaster): string | null {
  const units = [...(master.allies_config ?? []), ...master.enemy_config.enemies];
  const bad = units.find(
    (u) =>
      !u.name ||
      ![u.max_hp, u.armor, u.mobility, u.weapon.power, u.weapon.range, u.weapon.accuracy].every(Number.isFinite) ||
      u.max_hp <= 0
  );
  if (bad) return `作戦の機体「${bad.name || "（名前なし）"}」の値が不正です。`;
  const required = master.objective?.params.required;
  if (required !== undefined && !(Number.isInteger(required) && (required as number) >= 0)) {
    return "作戦目標の必要数は 0 以上の整数にしてください。";
  }
  return null;
}

function toItems(units: LocalSimMissionUnit[] | null | undefined, side: Side): UnitItem[] {
  return (units ?? []).map((unit, i) => ({ key: `${side}-${i}`, unit, original: unit }));
}

interface UnitFieldsProps {
  item: UnitItem;
  onChange: (unit: LocalSimMissionUnit) => void;
  onDuplicate: () => void;
  onRemove: () => void;
}

function UnitFields({ item, onChange, onDuplicate, onRemove }: UnitFieldsProps) {
  const { unit, original } = item;
  const weapon = unit.weapon;
  const setWeapon = (patch: Partial<LocalSimMissionUnit["weapon"]>) => onChange({ ...unit, weapon: { ...weapon, ...patch } });
  return (
    <div className="border border-[#00ff41]/20 p-2 space-y-2">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <TextField label="機体名" value={unit.name} original={original?.name} onChange={(name) => onChange({ ...unit, name })} />
        <NumberField label="最大 HP" value={unit.max_hp} original={original?.max_hp} onChange={(max_hp) => onChange({ ...unit, max_hp })} />
        <NumberField label="装甲" value={unit.armor} original={original?.armor} onChange={(armor) => onChange({ ...unit, armor })} />
        <NumberField label="機動性" step="0.01" value={unit.mobility} original={original?.mobility} onChange={(mobility) => onChange({ ...unit, mobility })} />
        <SelectField label="ロール" value={unit.role ?? ""} original={original ? (original.role ?? "") : undefined} options={ROLE_OPTIONS} onChange={(role) => onChange({ ...unit, role: role || null })} />
        <TextField label="小隊" value={unit.squad_id ?? ""} original={original ? (original.squad_id ?? "") : undefined} onChange={(squad) => onChange({ ...unit, squad_id: squad || null })} />
        <NumberField label="武器の威力" value={weapon.power} original={original?.weapon.power} onChange={(power) => setWeapon({ power })} />
        <NumberField label="武器の射程" value={weapon.range} original={original?.weapon.range} onChange={(range) => setWeapon({ range })} />
        <NumberField label="武器の命中率" value={weapon.accuracy} original={original?.weapon.accuracy} onChange={(accuracy) => setWeapon({ accuracy })} />
      </div>
      <div className="flex gap-3 text-xs">
        <button type="button" onClick={onDuplicate} className="text-[#00ff41]/70 hover:underline">
          複製
        </button>
        <button type="button" onClick={onRemove} className="text-red-400 hover:underline">
          外す
        </button>
        {!original && <span className="text-[#ffb000]">追加した機体</span>}
      </div>
    </div>
  );
}

interface RosterMissionEditorProps {
  /** 編集を始める時点の作戦マスター */
  master: LocalSimMissionMaster;
  onChange: (master: LocalSimMissionMaster) => void;
}

/** 作戦マスターの友軍・敵機（機体の値・ロール・小隊）と、作戦目標の必要数の編集欄 */
export default function RosterMissionEditor({ master, onChange }: RosterMissionEditorProps) {
  const [allies, setAllies] = useState<UnitItem[]>(() => toItems(master.allies_config, "allies"));
  const [enemies, setEnemies] = useState<UnitItem[]>(() => toItems(master.enemy_config.enemies, "enemies"));
  const [nextKey, setNextKey] = useState(0);
  const originalRequired = master.objective?.params.required;
  const [required, setRequired] = useState<unknown>(originalRequired);

  function emit(next: { allies?: UnitItem[]; enemies?: UnitItem[]; required?: unknown }) {
    const nextAllies = next.allies ?? allies;
    const nextEnemies = next.enemies ?? enemies;
    const nextRequired = "required" in next ? next.required : required;
    const params = { ...master.objective?.params };
    if (nextRequired === undefined) delete params.required;
    else params.required = nextRequired;
    onChange({
      ...master,
      // 友軍が null（なし）のまま、触っていなければ null を保つ。
      allies_config: master.allies_config === null && nextAllies.length === 0 ? null : nextAllies.map((i) => i.unit),
      enemy_config: { ...master.enemy_config, enemies: nextEnemies.map((i) => i.unit) },
      objective: master.objective ? { ...master.objective, params } : null,
    });
  }

  function update(side: Side, items: UnitItem[]) {
    if (side === "allies") setAllies(items);
    else setEnemies(items);
    emit(side === "allies" ? { allies: items } : { enemies: items });
  }

  function renderList(side: Side, items: UnitItem[]) {
    return (
      <div className="space-y-2">
        {items.length === 0 && <p className="text-xs text-[#00ff41]/50">なし</p>}
        {items.map((item, index) => (
          <UnitFields
            key={item.key}
            item={item}
            onChange={(unit) => update(side, items.map((i) => (i === item ? { ...i, unit } : i)))}
            onDuplicate={() => {
              const position = item.unit.position as { x: number } | undefined;
              // 同じ位置に重ねないよう、複製は少しずらす。
              const unit = structuredClone(item.unit);
              if (position) (unit.position as { x: number }).x = position.x + 50;
              setNextKey(nextKey + 1);
              update(side, [
                ...items.slice(0, index + 1),
                { key: `${side}-new-${nextKey}`, unit, original: null },
                ...items.slice(index + 1),
              ]);
            }}
            onRemove={() => update(side, items.filter((i) => i !== item))}
          />
        ))}
      </div>
    );
  }

  const requiredChanged = !Object.is(required, originalRequired);
  return (
    <div className="space-y-4 text-sm">
      <div>
        <p className="text-xs text-[#ffb000] font-bold mb-1">友軍 ({allies.length} 機)</p>
        {renderList("allies", allies)}
      </div>
      <div>
        <p className="text-xs text-[#ffb000] font-bold mb-1">敵機 ({enemies.length} 機)</p>
        {renderList("enemies", enemies)}
      </div>
      {master.objective && (
        <div className="max-w-xs">
          <p className="text-xs text-[#ffb000] font-bold mb-1">作戦目標: {master.objective.type}</p>
          <label className="block text-xs text-[#ffb000]/80 mb-0.5">
            必要数（空欄は既定）
            {requiredChanged && <span className="ml-1 text-[10px] text-[#ffb000]">元: {String(originalRequired ?? "既定")}</span>}
          </label>
          <input
            type="number"
            min={0}
            step={1}
            value={required === undefined ? "" : String(required)}
            onChange={(e) => {
              const value = e.target.value.trim() === "" ? undefined : Number(e.target.value);
              setRequired(value);
              emit({ required: value });
            }}
            className={`w-full bg-[#0a0a0a] border text-[#00ff41] px-2 py-1 text-sm font-mono ${
              requiredChanged ? "border-[#ffb000] bg-[#ffb000]/10" : "border-[#00ff41]/30"
            }`}
          />
        </div>
      )}
    </div>
  );
}
