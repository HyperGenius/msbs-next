/* frontend/tests/unit/weaponEditFormValidation.test.ts */
import { describe, it, expect } from "vitest";
import { masterWeaponSchema } from "@/components/admin/WeaponEditForm";

// ============================================================
// テストデータ
// ============================================================

const validWeaponSpec = {
  id: "beam_rifle",
  name: "Beam Rifle",
  power: 300,
  range: 600,
  accuracy: 80,
  type: "BEAM" as const,
  weapon_type: "RANGED" as const,
  optimal_range: 400,
  decay_rate: 0.05,
  is_melee: false,
  max_ammo: null,
  en_cost: 0,
  cooldown_sec: 1.5,
  fire_arc_deg: 30.0,
};

const validMasterWeapon = {
  id: "beam_rifle",
  name: "Beam Rifle",
  price: 800,
  description: "ガンダム用ビームライフル。",
  weapon: validWeaponSpec,
};

// ============================================================
// masterWeaponSchema テスト (エントリーレベル)
// ============================================================

describe("masterWeaponSchema — エントリー基本情報", () => {
  it("有効な武器エントリーを受け入れる", () => {
    const result = masterWeaponSchema.safeParse(validMasterWeapon);
    expect(result.success).toBe(true);
  });

  it("id が空の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validMasterWeapon, id: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("id"))).toBe(true);
  });

  it("id がスネークケース以外の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validMasterWeapon, id: "Beam-Rifle" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("id"))).toBe(true);
  });

  it("id にスペースが含まれる場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validMasterWeapon, id: "beam rifle" });
    expect(result.success).toBe(false);
  });

  it("name が空の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validMasterWeapon, name: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("name"))).toBe(true);
  });

  it("price が負の値の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse({ ...validMasterWeapon, price: -100 });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("price"))).toBe(true);
  });

  it("price が 0 は許可される", () => {
    const result = masterWeaponSchema.safeParse({ ...validMasterWeapon, price: 0 });
    expect(result.success).toBe(true);
  });

  it("description が空文字は許可される", () => {
    const result = masterWeaponSchema.safeParse({ ...validMasterWeapon, description: "" });
    expect(result.success).toBe(true);
  });
});

// ============================================================
// masterWeaponSchema テスト (weapon スペック)
// ============================================================

describe("masterWeaponSchema — weapon スペック", () => {
  function withWeapon(patch: Partial<typeof validWeaponSpec>) {
    return { ...validMasterWeapon, weapon: { ...validWeaponSpec, ...patch } };
  }

  it("weapon.id が空の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ id: "" }));
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("id"))).toBe(true);
  });

  it("weapon.id がスネークケース以外の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ id: "Beam-Rifle" }));
    expect(result.success).toBe(false);
  });

  it("weapon.name が空の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ name: "" }));
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("name"))).toBe(true);
  });

  it("weapon.power が 0 以下の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ power: 0 }));
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("power"))).toBe(true);
  });

  it("weapon.power が正値の場合は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ power: 1 }));
    expect(result.success).toBe(true);
  });

  it("weapon.range が 0 以下の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ range: 0 }));
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("range"))).toBe(true);
  });

  it("weapon.accuracy が 0 は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ accuracy: 0 }));
    expect(result.success).toBe(true);
  });

  it("weapon.accuracy が 100 は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ accuracy: 100 }));
    expect(result.success).toBe(true);
  });

  it("weapon.accuracy が 100 超の場合はエラー", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ accuracy: 101 }));
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("accuracy"))).toBe(true);
  });

  it("weapon.type が BEAM/PHYSICAL 以外はエラー", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ type: "LASER" as "BEAM" }));
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("type"))).toBe(true);
  });

  it("weapon.weapon_type が MELEE は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ weapon_type: "MELEE" }));
    expect(result.success).toBe(true);
  });

  it("weapon.weapon_type が CLOSE_RANGE は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ weapon_type: "CLOSE_RANGE" }));
    expect(result.success).toBe(true);
  });

  it("weapon.is_melee が boolean 以外はエラー", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ is_melee: "yes" as unknown as boolean }));
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("is_melee"))).toBe(true);
  });

  it("weapon.optimal_range が 0 は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ optimal_range: 0 }));
    expect(result.success).toBe(true);
  });

  it("weapon.decay_rate が 0 は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ decay_rate: 0 }));
    expect(result.success).toBe(true);
  });

  it("weapon.max_ammo が null は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ max_ammo: null }));
    expect(result.success).toBe(true);
  });

  it("weapon.max_ammo が正整数は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ max_ammo: 8 }));
    expect(result.success).toBe(true);
  });

  it("weapon.en_cost が 0 は許可される", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ en_cost: 0 }));
    expect(result.success).toBe(true);
  });

  it("weapon.cooldown_sec が 0 は許可される（連射可能）", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ cooldown_sec: 0 }));
    expect(result.success).toBe(true);
  });

  it("weapon.fire_arc_deg が 360 は許可される（全方位）", () => {
    const result = masterWeaponSchema.safeParse(withWeapon({ fire_arc_deg: 360 }));
    expect(result.success).toBe(true);
  });
});
