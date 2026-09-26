/* admin-tool/tests/unit/npcMobileSuitEditFormValidation.test.ts */
import { describe, it, expect } from "vitest";
import {
  npcMobileSuitSchema,
  toNpcMobileSuitFormValues,
  toNpcMobileSuitPayload,
} from "@/components/admin/NpcMobileSuitEditForm";
import { masterToSpecValues } from "@/components/admin/MobileSuitSpecFields";
import { masterMobileSuitLabel } from "@/components/admin/MasterMobileSuitSelect";
import { MasterMobileSuit, NpcMobileSuit } from "@/types/admin";

// ============================================================
// テストデータ
// ============================================================

const npcSuit: NpcMobileSuit = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Dom (NPC)",
  max_hp: 800,
  current_hp: 800,
  armor: 50,
  mobility: 1.1,
  sensor_range: 500,
  beam_resistance: 0,
  physical_resistance: 0.1,
  max_en: 1000,
  en_recovery: 100,
  melee_aptitude: 1,
  shooting_aptitude: 1,
  accuracy_bonus: 0,
  evasion_bonus: 0,
  acceleration_bonus: 1,
  turning_bonus: 1,
  tactics: { priority: "WEAKEST", range: "MELEE" },
  missing_parts: [],
  weapons: [
    {
      id: "npc_weapon_abcd1234",
      name: "Heat Hawk",
      power: 150,
      range: 100,
      accuracy: 80,
      type: "PHYSICAL",
      weapon_type: "MELEE",
      fire_arc_deg: 360,
    },
  ],
  personality: "AGGRESSIVE",
  is_ace: false,
  ace_id: null,
  pilot_name: "John Doe",
  bounty_exp: 0,
  bounty_credits: 0,
};

const master: MasterMobileSuit = {
  id: "gelgoog",
  name: "Gelgoog",
  name_ja: "ゲルググ",
  model_number: "MS-14A",
  price: 3000,
  faction: "ZEON",
  description: "",
  weapon_slot_count: 2,
  beam_generator_lv: 1,
  flavor_text: null,
  specs: {
    max_hp: 1100,
    armor: 70,
    mobility: 1.4,
    sensor_range: 600,
    beam_resistance: 0.1,
    physical_resistance: 0.1,
    melee_aptitude: 1,
    shooting_aptitude: 1,
    accuracy_bonus: 0,
    evasion_bonus: 0,
    acceleration_bonus: 1,
    turning_bonus: 1,
    missing_parts: ["HEAD"],
    weapons: [{ id: "beam_rifle", name: "Beam Rifle", power: 220, range: 600, accuracy: 75, type: "BEAM" }],
  },
};

// ============================================================
// toNpcMobileSuitFormValues / npcMobileSuitSchema
// ============================================================

describe("toNpcMobileSuitFormValues", () => {
  it("変換結果はそのままバリデーションを通過する", () => {
    expect(npcMobileSuitSchema.safeParse(toNpcMobileSuitFormValues(npcSuit)).success).toBe(true);
  });

  it("戦術が未設定の機体は既定値で補完する", () => {
    const values = toNpcMobileSuitFormValues({ ...npcSuit, tactics: {} });
    expect(values.mobile_suit.tactics).toEqual({ priority: "CLOSEST", range: "BALANCED" });
  });
});

describe("npcMobileSuitSchema", () => {
  it("武器が0件の場合はエラー", () => {
    const values = toNpcMobileSuitFormValues({ ...npcSuit, weapons: [] });
    expect(npcMobileSuitSchema.safeParse(values).success).toBe(false);
  });

  it("適性が0以下の場合はエラー", () => {
    const values = toNpcMobileSuitFormValues({ ...npcSuit, melee_aptitude: 0 });
    expect(npcMobileSuitSchema.safeParse(values).success).toBe(false);
  });
});

// ============================================================
// toNpcMobileSuitPayload
// ============================================================

describe("toNpcMobileSuitPayload", () => {
  it("フォームで扱わない武器項目は同じ武器IDの既存値を引き継ぐ", () => {
    const values = toNpcMobileSuitFormValues(npcSuit);
    values.mobile_suit.weapons[0].power = 999;
    const payload = toNpcMobileSuitPayload(values, npcSuit);
    const weapon = payload.weapons![0];
    expect(weapon.power).toBe(999);
    expect(weapon.weapon_type).toBe("MELEE");
    expect(weapon.fire_arc_deg).toBe(360);
  });

  it("適性・補正を含む全項目を送る", () => {
    const values = toNpcMobileSuitFormValues(npcSuit);
    values.mobile_suit.accuracy_bonus = 5;
    const payload = toNpcMobileSuitPayload(values, npcSuit);
    expect(payload.accuracy_bonus).toBe(5);
    expect(payload.tactics).toEqual({ priority: "WEAKEST", range: "MELEE" });
  });
});

// ============================================================
// 機体マスターからの取り込み
// ============================================================

describe("masterToSpecValues", () => {
  it("機体マスターのスペックと武装で上書きし、EN と戦術は現在の値を残す", () => {
    const current = toNpcMobileSuitFormValues(npcSuit).mobile_suit;
    const next = masterToSpecValues(master, current);
    expect(next.name).toBe("Gelgoog");
    expect(next.max_hp).toBe(1100);
    expect(next.missing_parts).toEqual(["HEAD"]);
    expect(next.weapons.map((w) => w.id)).toEqual(["beam_rifle"]);
    expect(next.max_en).toBe(current.max_en);
    expect(next.tactics).toEqual(current.tactics);
  });
});

describe("masterMobileSuitLabel", () => {
  it("日本語名と型番を表示する", () => {
    expect(masterMobileSuitLabel(master)).toBe("ゲルググ (MS-14A)");
  });

  it("日本語名が無ければ英語名を表示する", () => {
    expect(masterMobileSuitLabel({ ...master, name_ja: "" })).toBe("Gelgoog");
  });
});
