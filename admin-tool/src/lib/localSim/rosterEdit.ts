/* admin-tool/src/lib/localSim/rosterEdit.ts */
// ロスターの機体（entries[].snapshot）を NPC 機と同じフォームで編集するための変換と、元の値との比較。
import type { NpcMobileSuit } from "@/types/admin";
import type { Tactics, Weapon } from "@/types/weapon";
import type { LocalSimRosterEntry } from "@/types/localSim";
import { mergeTactics, mergeWeaponSources, npcMobileSuitToSpecValues } from "@/components/admin/MobileSuitSpecFields";
import type { NpcMobileSuitFormValues } from "@/components/admin/NpcMobileSuitEditForm";

type Snapshot = Record<string, unknown>;

export function snapshotToFormValues(snapshot: Snapshot): NpcMobileSuitFormValues {
  const ms = snapshot as unknown as NpcMobileSuit;
  return {
    mobile_suit: {
      ...npcMobileSuitToSpecValues({
        ...ms,
        tactics: ms.tactics ?? {},
        weapons: ms.weapons ?? [],
        missing_parts: ms.missing_parts ?? [],
        // スロット数が無い古いスナップショットは、装備数と 2 の大きい方（backend の resolve_weapon_slot_count と同じ）にする。
        weapon_slot_count: ms.weapon_slot_count ?? Math.max((ms.weapons ?? []).length, 2),
      }),
      melee_aptitude: ms.melee_aptitude ?? 1,
      shooting_aptitude: ms.shooting_aptitude ?? 1,
      accuracy_bonus: ms.accuracy_bonus ?? 0,
      evasion_bonus: ms.evasion_bonus ?? 0,
      acceleration_bonus: ms.acceleration_bonus ?? 1,
      turning_bonus: ms.turning_bonus ?? 1,
    },
  };
}

/**
 * フォーム値を元のスナップショットに重ねる。
 * フォームで扱わない項目（位置・team_id・武器の weapon_type など）は元の値を引き継ぐ。
 * 最大 HP を変えたときは現在 HP も揃える（NPC 機の編集と同じ）。
 */
export function formValuesToSnapshot(
  values: NpcMobileSuitFormValues,
  original: Snapshot,
  importedWeapons: Weapon[] = []
): Snapshot {
  const { master_mobile_suit_id, ...spec } = values.mobile_suit;
  const originalWeapons = (original.weapons as Weapon[] | undefined) ?? [];
  const snapshot: Snapshot = {
    ...original,
    ...spec,
    tactics: mergeTactics(spec.tactics, original.tactics as Partial<Tactics> | undefined),
    weapons: mergeWeaponSources(spec.weapons, [...originalWeapons, ...importedWeapons]),
  };
  if (master_mobile_suit_id !== null || "master_mobile_suit_id" in original) {
    snapshot.master_mobile_suit_id = master_mobile_suit_id;
  }
  if (spec.max_hp !== original.max_hp) snapshot.current_hp = spec.max_hp;
  return snapshot;
}

/** 複製した機体の ID。同じ ID の機体が 2 機いると、戦闘のユニットが衝突する。 */
export function duplicateEntry(entry: LocalSimRosterEntry): LocalSimRosterEntry {
  const copy = structuredClone(entry);
  const id = crypto.randomUUID();
  copy.snapshot.id = id;
  return copy;
}

export interface ValueChange {
  path: string;
  before: unknown;
  after: unknown;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * 2 つの JSON 値を比べ、変わった葉の値を返す。
 * 武装は配列の位置ではなく武器 ID で対応させる（並べ替えや追加・削除で全件が変わったように見せない）。
 */
export function diffValues(before: unknown, after: unknown, path = ""): ValueChange[] {
  if (Array.isArray(before) && Array.isArray(after) && [...before, ...after].every((v) => isObject(v) && "id" in v)) {
    const beforeById = new Map(before.map((v) => [String(v.id), v]));
    const afterById = new Map(after.map((v) => [String(v.id), v]));
    const ids = [...new Set([...beforeById.keys(), ...afterById.keys()])];
    return ids.flatMap((id) => diffValues(beforeById.get(id), afterById.get(id), `${path}[${id}]`));
  }
  if (Array.isArray(before) && Array.isArray(after)) {
    const length = Math.max(before.length, after.length);
    return Array.from({ length }, (_, i) => diffValues(before[i], after[i], `${path}[${i}]`)).flat();
  }
  if (isObject(before) && isObject(after)) {
    const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])];
    return keys.flatMap((key) => diffValues(before[key], after[key], path ? `${path}.${key}` : key));
  }
  return JSON.stringify(before) === JSON.stringify(after) ? [] : [{ path, before, after }];
}

export function formatChangeValue(value: unknown): string {
  if (value === undefined) return "（なし）";
  if (value === null) return "null";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
