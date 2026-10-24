import { describe, it, expect } from "vitest";
import { diffValues, duplicateEntry, formValuesToSnapshot, snapshotToFormValues } from "@/lib/localSim/rosterEdit";

const snapshot = {
  id: "unit-1",
  name: "ザク",
  max_hp: 800,
  current_hp: 800,
  armor: 40,
  mobility: 1,
  sensor_range: 500,
  beam_resistance: 0,
  physical_resistance: 0,
  max_en: 1000,
  en_recovery: 100,
  melee_aptitude: 1,
  shooting_aptitude: 1,
  accuracy_bonus: 0,
  evasion_bonus: 0,
  acceleration_bonus: 1,
  turning_bonus: 1,
  team_id: "A",
  position: { x: 1, y: 2, z: 3 },
  tactics: { priority: "CLOSEST", range: "BALANCED", legacy: "keep" },
  missing_parts: [],
  weapon_slot_count: 2,
  weapons: [
    { id: "w1", name: "Rifle", power: 100, range: 500, accuracy: 70, weapon_type: "RANGED", aim_distribution: { TORSO: 1 } },
  ],
};

describe("formValuesToSnapshot", () => {
  it("フォームで扱わない項目を元のスナップショットから引き継ぐ", () => {
    const values = snapshotToFormValues(snapshot);
    values.mobile_suit.armor = 99;
    const edited = formValuesToSnapshot(values, snapshot);
    expect(edited.armor).toBe(99);
    expect(edited.team_id).toBe("A");
    expect(edited.position).toEqual({ x: 1, y: 2, z: 3 });
    expect(edited.tactics).toMatchObject({ legacy: "keep" });
    expect((edited.weapons as { weapon_type: string }[])[0].weapon_type).toBe("RANGED");
  });
  it("最大 HP を変えると現在 HP も揃える", () => {
    const values = snapshotToFormValues(snapshot);
    values.mobile_suit.max_hp = 1000;
    expect(formValuesToSnapshot(values, snapshot).current_hp).toBe(1000);
  });
  it("武装の狙う部位配分を割合で書き戻す", () => {
    const values = snapshotToFormValues(snapshot);
    expect(values.mobile_suit.weapons[0].aim_distribution.TORSO).toBe(100);
    const edited = formValuesToSnapshot(values, snapshot);
    expect((edited.weapons as { aim_distribution: Record<string, number> }[])[0].aim_distribution.TORSO).toBe(1);
  });
});

describe("diffValues", () => {
  it("変えた値だけを返す", () => {
    expect(diffValues({ a: 1, b: { c: 2 } }, { a: 1, b: { c: 3 } })).toEqual([{ path: "b.c", before: 2, after: 3 }]);
  });
  it("武装は武器 ID で対応させる", () => {
    const before = [{ id: "w1", power: 1 }, { id: "w2", power: 2 }];
    const after = [{ id: "w2", power: 2 }, { id: "w1", power: 5 }];
    expect(diffValues(before, after)).toEqual([{ path: "[w1].power", before: 1, after: 5 }]);
  });
  it("追加した武装は項目ごとに「なし」からの変更として返す", () => {
    const changes = diffValues([{ id: "w1" }], [{ id: "w1" }, { id: "w2" }]);
    expect(changes).toEqual([{ path: "[w2]", before: undefined, after: { id: "w2" } }]);
  });
});

describe("duplicateEntry", () => {
  it("別の ID を付け、元の機体は変えない", () => {
    const entry = { source: { kind: "npc", mobile_suit_id: "x" }, is_npc: true, snapshot: { ...snapshot } };
    const copy = duplicateEntry(entry);
    expect(copy.snapshot.id).not.toBe("unit-1");
    expect(entry.snapshot.id).toBe("unit-1");
  });
});
