import { describe, it, expect } from "vitest";
import { getWeaponWarnings } from "@/lib/weaponWarnings";
import { WeaponSpec } from "@/types/weapon";

const base: WeaponSpec = { power: 100, range: 300, accuracy: 70 };
const codes = (spec: WeaponSpec) => getWeaponWarnings(spec).map((w) => w.code);

describe("getWeaponWarnings", () => {
  it("max_ammo が未設定・null・0 の実弾武器は弾数未設定", () => {
    expect(codes({ ...base, type: "PHYSICAL" })).toEqual(["NO_MAX_AMMO"]);
    expect(codes({ ...base, type: "PHYSICAL", max_ammo: null })).toEqual(["NO_MAX_AMMO"]);
    expect(codes({ ...base, type: "PHYSICAL", max_ammo: 0 })).toEqual(["NO_MAX_AMMO"]);
  });

  it("max_ammo がある実弾武器は警告しない", () => {
    expect(codes({ ...base, type: "PHYSICAL", max_ammo: 8 })).toEqual([]);
  });

  it("en_cost が未設定・0 のビーム武器は EN消費なし", () => {
    expect(codes({ ...base, type: "BEAM" })).toEqual(["NO_EN_COST"]);
    expect(codes({ ...base, type: "BEAM", en_cost: 0 })).toEqual(["NO_EN_COST"]);
  });

  it("en_cost があるビーム武器は警告しない。弾数は見ない", () => {
    expect(codes({ ...base, type: "BEAM", en_cost: 20 })).toEqual([]);
  });

  it("近接武器は警告しない", () => {
    expect(codes({ ...base, type: "PHYSICAL", is_melee: true })).toEqual([]);
    expect(codes({ ...base, type: "BEAM", weapon_type: "MELEE" })).toEqual([]);
  });
});
