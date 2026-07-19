/* frontend/tests/unit/mobileSuitEditFormValidation.test.ts */
import { describe, it, expect } from "vitest";
import { masterMobileSuitSchema, weaponSchema } from "@/components/admin/MobileSuitEditForm";

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
  optimal_range: 320,
  decay_rate: 0.09,
  is_melee: false,
  en_cost: 10,
  cool_down_turn: 0,
};

const validMobileSuit = {
  id: "rx_78_2",
  name: "RX-78-2 Gundam",
  price: 1500,
  faction: "FEDERATION",
  description: "宇宙世紀を代表するモビルスーツ。",
  specs: {
    max_hp: 1000,
    armor: 80,
    mobility: 1.2,
    sensor_range: 600,
    beam_resistance: 0.1,
    physical_resistance: 0.2,
    melee_aptitude: 1.2,
    shooting_aptitude: 1.3,
    accuracy_bonus: 5.0,
    evasion_bonus: 0.0,
    acceleration_bonus: 1.0,
    turning_bonus: 1.0,
    weapons: [validWeapon],
  },
};

// ============================================================
// weaponSchema テスト
// ============================================================

describe("weaponSchema", () => {
  it("有効な武器データを受け入れる", () => {
    const result = weaponSchema.safeParse(validWeapon);
    expect(result.success).toBe(true);
  });

  it("id が空の場合はエラー", () => {
    const result = weaponSchema.safeParse({ ...validWeapon, id: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toContain("id");
  });

  it("id がスネークケース以外の場合はエラー", () => {
    const result = weaponSchema.safeParse({ ...validWeapon, id: "Beam-Rifle" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toContain("id");
  });

  it("name が空の場合はエラー", () => {
    const result = weaponSchema.safeParse({ ...validWeapon, name: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toContain("name");
  });

  it("power が 0 以下の場合はエラー", () => {
    const result = weaponSchema.safeParse({ ...validWeapon, power: 0 });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toContain("power");
  });

  it("accuracy が 100 超の場合はエラー", () => {
    const result = weaponSchema.safeParse({ ...validWeapon, accuracy: 101 });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toContain("accuracy");
  });

  it("type が BEAM/PHYSICAL 以外はエラー", () => {
    const result = weaponSchema.safeParse({ ...validWeapon, type: "LASER" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toContain("type");
  });

  it("is_melee が boolean 以外はエラー", () => {
    const result = weaponSchema.safeParse({ ...validWeapon, is_melee: "yes" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toContain("is_melee");
  });
});

// ============================================================
// masterMobileSuitSchema テスト
// ============================================================

describe("masterMobileSuitSchema", () => {
  it("有効な機体データを受け入れる", () => {
    const result = masterMobileSuitSchema.safeParse(validMobileSuit);
    expect(result.success).toBe(true);
  });

  it("id が空の場合はエラー", () => {
    const result = masterMobileSuitSchema.safeParse({ ...validMobileSuit, id: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("id"))).toBe(true);
  });

  it("id がスネークケース以外の場合はエラー", () => {
    const result = masterMobileSuitSchema.safeParse({ ...validMobileSuit, id: "RX-78-2" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("id"))).toBe(true);
  });

  it("id にスペースが含まれる場合はエラー", () => {
    const result = masterMobileSuitSchema.safeParse({ ...validMobileSuit, id: "rx 78 2" });
    expect(result.success).toBe(false);
  });

  it("name が空の場合はエラー", () => {
    const result = masterMobileSuitSchema.safeParse({ ...validMobileSuit, name: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("name"))).toBe(true);
  });

  it("price が負の値の場合はエラー", () => {
    const result = masterMobileSuitSchema.safeParse({ ...validMobileSuit, price: -100 });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("price"))).toBe(true);
  });

  it("price が 0 は許可される", () => {
    const result = masterMobileSuitSchema.safeParse({ ...validMobileSuit, price: 0 });
    expect(result.success).toBe(true);
  });

  it("specs.max_hp が 0 以下の場合はエラー", () => {
    const result = masterMobileSuitSchema.safeParse({
      ...validMobileSuit,
      specs: { ...validMobileSuit.specs, max_hp: 0 },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("max_hp"))).toBe(true);
  });

  it("specs.mobility が 0 の場合はエラー", () => {
    const result = masterMobileSuitSchema.safeParse({
      ...validMobileSuit,
      specs: { ...validMobileSuit.specs, mobility: 0 },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("mobility"))).toBe(true);
  });

  it("specs.beam_resistance が 1 超の場合はエラー", () => {
    const result = masterMobileSuitSchema.safeParse({
      ...validMobileSuit,
      specs: { ...validMobileSuit.specs, beam_resistance: 1.5 },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("beam_resistance"))).toBe(true);
  });

  it("specs.weapons が空配列の場合はエラー", () => {
    const result = masterMobileSuitSchema.safeParse({
      ...validMobileSuit,
      specs: { ...validMobileSuit.specs, weapons: [] },
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("weapons"))).toBe(true);
  });

  it("specs.weapons が複数のとき全て有効ならOK", () => {
    const result = masterMobileSuitSchema.safeParse({
      ...validMobileSuit,
      specs: {
        ...validMobileSuit.specs,
        weapons: [
          validWeapon,
          {
            ...validWeapon,
            id: "beam_saber",
            name: "Beam Saber",
            type: "PHYSICAL",
            is_melee: true,
          },
        ],
      },
    });
    expect(result.success).toBe(true);
  });

  it("specs.weapons の中に無効な武器があればエラー", () => {
    const result = masterMobileSuitSchema.safeParse({
      ...validMobileSuit,
      specs: {
        ...validMobileSuit.specs,
        weapons: [
          validWeapon,
          { ...validWeapon, id: "InvalidWeapon-ID" }, // スネークケースでない
        ],
      },
    });
    expect(result.success).toBe(false);
  });

  it("faction が空文字は許可される", () => {
    const result = masterMobileSuitSchema.safeParse({ ...validMobileSuit, faction: "" });
    expect(result.success).toBe(true);
  });

  it("description が空文字は許可される", () => {
    const result = masterMobileSuitSchema.safeParse({ ...validMobileSuit, description: "" });
    expect(result.success).toBe(true);
  });

  it("accuracy_bonus が負値でも許可される", () => {
    const result = masterMobileSuitSchema.safeParse({
      ...validMobileSuit,
      specs: { ...validMobileSuit.specs, accuracy_bonus: -5.0 },
    });
    expect(result.success).toBe(true);
  });
});
