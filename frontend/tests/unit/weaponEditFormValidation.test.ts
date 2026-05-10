/* frontend/tests/unit/weaponEditFormValidation.test.ts */
import { describe, it, expect } from "vitest";
import { masterWeaponSchema } from "@/components/admin/WeaponEditForm";

// ============================================================
// テストデータ
// ============================================================

const validWeapon = {
  id: "beam_rifle",
  name: "Beam Rifle",
  power: 150,
  range: 500,
  accuracy: 75,
  type: "BEAM" as const,
  weapon_type: "RANGED" as const,
  optimal_range: 320,
  decay_rate: 0.09,
  is_melee: false,
  max_ammo: null,
  en_cost: 10,
  cool_down_turn: 0,
  cooldown_sec: 1.0,
  fire_arc_deg: 30.0,
};

const validEntry = {
  id: "beam_rifle",
  name: "Beam Rifle",
  price: 800,
  description: "高威力・高精度のビーム兵器。",
  weapon: validWeapon,
};

// ============================================================
// masterWeaponSchema テスト
// ============================================================

describe("masterWeaponSchema", () => {
  it("有効な武器エントリーを受け入れる", () => {
    const result = masterWeaponSchema.safeParse(validEntry);
    expect(result.success).toBe(true);
  });

  // --- id バリデーション ---

  it("id が空の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validEntry, id: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("id"))).toBe(true);
  });

  it("id がスネークケース以外の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validEntry, id: "Beam-Rifle" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("id"))).toBe(true);
  });

  it("id にスペースが含まれる場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validEntry, id: "beam rifle" });
    expect(result.success).toBe(false);
  });

  // --- name バリデーション ---

  it("name が空の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validEntry, name: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("name"))).toBe(true);
  });

  // --- price バリデーション ---

  it("price が負の値の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validEntry, price: -100 });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("price"))).toBe(true);
  });

  it("price が 0 は許可される", () => {
    const result = masterWeaponSchema.safeParse({ ...validEntry, price: 0 });
    expect(result.success).toBe(true);
  });

  // --- weapon サブフィールド ---

  it("weapon.id が空の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, id: "" },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("id"))).toBe(true);
  });

  it("weapon.id がスネークケース以外の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, id: "Beam-Rifle-ID" },
    });
    expect(result.success).toBe(false);
  });

  it("weapon.power が 0 以下の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, power: 0 },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("power"))).toBe(true);
  });

  it("weapon.range が 0 以下の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, range: -1 },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("range"))).toBe(true);
  });

  it("weapon.accuracy が 100 超の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, accuracy: 101 },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("accuracy"))).toBe(true);
  });

  it("weapon.accuracy が 0 は許可される", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, accuracy: 0 },
    });
    expect(result.success).toBe(true);
  });

  it("weapon.type が BEAM/PHYSICAL 以外はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, type: "LASER" },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("type"))).toBe(true);
  });

  it("weapon.type が BEAM は許可される", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, type: "BEAM" },
    });
    expect(result.success).toBe(true);
  });

  it("weapon.type が PHYSICAL は許可される", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, type: "PHYSICAL" },
    });
    expect(result.success).toBe(true);
  });

  it("weapon.weapon_type が MELEE/CLOSE_RANGE/RANGED 以外はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, weapon_type: "INVALID" },
    });
    expect(result.success).toBe(false);
  });

  it("weapon.weapon_type が MELEE は許可される", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, weapon_type: "MELEE", is_melee: true },
    });
    expect(result.success).toBe(true);
  });

  it("weapon.is_melee が boolean 以外はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, is_melee: "yes" },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("is_melee"))).toBe(true);
  });

  it("weapon.decay_rate が負の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, decay_rate: -0.1 },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("decay_rate"))).toBe(true);
  });

  it("weapon.fire_arc_deg が 360 超の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, fire_arc_deg: 361 },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("fire_arc_deg"))).toBe(true);
  });

  it("weapon.fire_arc_deg が 360 は許可される（全周囲）", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, fire_arc_deg: 360 },
    });
    expect(result.success).toBe(true);
  });

  it("weapon.max_ammo が null は許可される（無限弾）", () => {
    const result = masterWeaponSchema.safeParse({
      ...validEntry,
      weapon: { ...validWeapon, max_ammo: null },
    });
    expect(result.success).toBe(true);
  });

  it("description が空文字は許可される", () => {
    const result = masterWeaponSchema.safeParse({ ...validEntry, description: "" });
    expect(result.success).toBe(true);
  });
});
