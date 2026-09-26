/* admin-tool/tests/unit/acePilotEditFormValidation.test.ts */
import { describe, it, expect } from "vitest";
import { acePilotSchema, toAcePilotPayload, AcePilotFormValues } from "@/components/admin/AcePilotEditForm";
import { AcePilot } from "@/types/admin";

// ============================================================
// テストデータ
// ============================================================

const validFormValues: AcePilotFormValues = {
  id: "ace_char_aznable",
  name: "赤い彗星",
  pilot_name: "Char Aznable",
  description: "通常の3倍の速度を持つエースパイロット",
  personality: "AGGRESSIVE",
  bounty_exp: 500,
  bounty_credits: 1000,
  stats: { sht: 10, mel: 10, intel: 9, ref: 15, tou: 7, luk: 8 },
  skills: [{ id: "flanking", level: 3 }],
  mobile_suit: {
    name: "High Mobility Zaku II (Red)",
    max_hp: 1200,
    armor: 80,
    mobility: 3.0,
    sensor_range: 700,
    beam_resistance: 0.1,
    physical_resistance: 0.25,
    max_en: 1500,
    en_recovery: 150,
    tactics: { priority: "WEAKEST", range: "MELEE" },
    missing_parts: [],
    weapons: [
      {
        id: "ace_zaku_mg",
        name: "High Mobility Zaku Machine Gun",
        power: 150,
        range: 500,
        accuracy: 85,
        type: "PHYSICAL",
        optimal_range: 350,
        decay_rate: 0.05,
        is_melee: false,
        en_cost: 0,
      },
    ],
  },
};

function withOverride(patch: (v: AcePilotFormValues) => void): AcePilotFormValues {
  const values = structuredClone(validFormValues);
  patch(values);
  return values;
}

// ============================================================
// acePilotSchema
// ============================================================

describe("acePilotSchema", () => {
  it("正常なデータはバリデーションを通過する", () => {
    expect(acePilotSchema.safeParse(validFormValues).success).toBe(true);
  });

  it("IDがsnake_caseでない場合はエラー", () => {
    const result = acePilotSchema.safeParse(withOverride((v) => (v.id = "Ace-Char")));
    expect(result.success).toBe(false);
  });

  it("武器が0件の場合はエラー", () => {
    const result = acePilotSchema.safeParse(withOverride((v) => (v.mobile_suit.weapons = [])));
    expect(result.success).toBe(false);
  });

  it("耐性が1を超える場合はエラー", () => {
    const result = acePilotSchema.safeParse(withOverride((v) => (v.mobile_suit.beam_resistance = 1.5)));
    expect(result.success).toBe(false);
  });

  it("スキルレベルが上限を超える場合はエラー", () => {
    const result = acePilotSchema.safeParse(withOverride((v) => (v.skills = [{ id: "flanking", level: 4 }])));
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].path).toEqual(["skills", 0, "level"]);
    }
  });

  it("同じスキルが重複している場合はエラー", () => {
    const result = acePilotSchema.safeParse(
      withOverride(
        (v) =>
          (v.skills = [
            { id: "flanking", level: 1 },
            { id: "flanking", level: 2 },
          ])
      )
    );
    expect(result.success).toBe(false);
  });
});

// ============================================================
// toAcePilotPayload
// ============================================================

describe("toAcePilotPayload", () => {
  it("skills 配列をスキルID→レベルの辞書に変換する", () => {
    const payload = toAcePilotPayload(
      withOverride(
        (v) =>
          (v.skills = [
            { id: "flanking", level: 3 },
            { id: "damage_up", level: 5 },
          ])
      ),
      null
    );
    expect(payload.skills).toEqual({ flanking: 3, damage_up: 5 });
  });

  it("フォームで扱わない武器項目は同じ武器IDの既存値を引き継ぐ", () => {
    const original = {
      ...validFormValues,
      skills: { flanking: 3 },
      mobile_suit: {
        ...validFormValues.mobile_suit,
        weapons: [{ ...validFormValues.mobile_suit.weapons[0], fire_arc_deg: 360, cooldown_sec: 0.5 }],
      },
    } as AcePilot;

    const payload = toAcePilotPayload(
      withOverride((v) => (v.mobile_suit.weapons[0].power = 999)),
      original
    );
    const weapon = payload.mobile_suit.weapons[0];
    expect(weapon.power).toBe(999);
    expect(weapon.fire_arc_deg).toBe(360);
    expect(weapon.cooldown_sec).toBe(0.5);
  });
});

describe("toAcePilotPayload (機体マスターから取り込んだ武装)", () => {
  it("取り込んだ武装のフォーム外項目を引き継ぐ", () => {
    const imported = [{ ...validFormValues.mobile_suit.weapons[0], weapon_type: "MELEE" as const, fire_arc_deg: 360 }];
    const payload = toAcePilotPayload(validFormValues, null, imported);
    expect(payload.mobile_suit.weapons[0].weapon_type).toBe("MELEE");
    expect(payload.mobile_suit.weapons[0].fire_arc_deg).toBe(360);
  });

  it("同じ武器IDでは既存エースより取り込み元の値を優先する", () => {
    const original = {
      ...validFormValues,
      skills: {},
      mobile_suit: {
        ...validFormValues.mobile_suit,
        weapons: [{ ...validFormValues.mobile_suit.weapons[0], cooldown_sec: 0.5 }],
      },
    } as AcePilot;
    const imported = [{ ...validFormValues.mobile_suit.weapons[0], cooldown_sec: 3.0 }];
    const payload = toAcePilotPayload(validFormValues, original, imported);
    expect(payload.mobile_suit.weapons[0].cooldown_sec).toBe(3.0);
  });
});
