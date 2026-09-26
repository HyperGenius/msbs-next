/* admin-tool/tests/unit/npcMobileSuitEditFormValidation.test.ts */
import { describe, it, expect } from "vitest";
import {
  npcMobileSuitSchema,
  toNpcMobileSuitFormValues,
  toNpcMobileSuitPayload,
} from "@/components/admin/NpcMobileSuitEditForm";
import {
  DEFAULT_AIM_DISTRIBUTION_PERCENT,
  masterMobileSuitValue,
  masterToSpecValues,
  masterWeaponToWeapon,
  uniqueWeaponId,
  weaponSlotLabel,
  weaponToFormValues,
} from "@/components/admin/MobileSuitSpecFields";
import { masterMobileSuitLabel } from "@/components/admin/MasterMobileSuitSelect";
import { MasterMobileSuit, MasterWeapon, NpcMobileSuit } from "@/types/admin";

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
  weapon_slot_count: 2,
  master_mobile_suit_id: null,
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
  blueprint: { is_standard_issue: true, duplicate_credit_value: 0 },
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
    expect(values.mobile_suit.tactics).toEqual({
      priority: "CLOSEST",
      range: "BALANCED",
      weapon_switch_policy: "BALANCED",
    });
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
    expect(payload.tactics).toEqual({ priority: "WEAKEST", range: "MELEE", weapon_switch_policy: "BALANCED" });
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
    expect(next.weapon_slot_count).toBe(2);
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

// ============================================================
// 武器スロット数・武器マスターからの追加 (Issue #543)
// ============================================================

const masterWeapon: MasterWeapon = {
  id: "zaku_mg",
  name: "Zaku Machine Gun",
  price: 500,
  description: "",
  flavor_text: null,
  blueprint: { is_standard_issue: true, duplicate_credit_value: 0 },
  weapon: {
    power: 120,
    range: 400,
    accuracy: 70,
    type: "PHYSICAL",
    weapon_type: "RANGED",
    cooldown_sec: 0.5,
    fire_arc_deg: 45,
    max_ammo: 60,
  },
};

describe("npcMobileSuitSchema (武器スロット数)", () => {
  it("武装の本数がスロット数を超える場合はエラー", () => {
    const values = toNpcMobileSuitFormValues({ ...npcSuit, weapon_slot_count: 1 });
    values.mobile_suit.weapons.push({ ...values.mobile_suit.weapons[0], id: "heat_hawk" });
    const result = npcMobileSuitSchema.safeParse(values);
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toEqual(["mobile_suit", "weapon_slot_count"]);
  });

  it("武装の本数がスロット数と同じなら通過する", () => {
    const values = toNpcMobileSuitFormValues(npcSuit);
    values.mobile_suit.weapons.push({ ...values.mobile_suit.weapons[0], id: "heat_hawk" });
    expect(npcMobileSuitSchema.safeParse(values).success).toBe(true);
  });

  it("同じ武器IDが2本ある場合はエラー", () => {
    const values = toNpcMobileSuitFormValues(npcSuit);
    values.mobile_suit.weapons.push({ ...values.mobile_suit.weapons[0] });
    expect(npcMobileSuitSchema.safeParse(values).success).toBe(false);
  });

  it("ビームジェネレータLv の条件は適用しない", () => {
    const values = toNpcMobileSuitFormValues(npcSuit);
    values.mobile_suit.weapons[0] = { ...values.mobile_suit.weapons[0], type: "BEAM", required_beam_generator_lv: 5 };
    expect(npcMobileSuitSchema.safeParse(values).success).toBe(true);
  });

  it("スロット数を送る", () => {
    const values = toNpcMobileSuitFormValues(npcSuit);
    values.mobile_suit.weapon_slot_count = 4;
    expect(toNpcMobileSuitPayload(values, npcSuit).weapon_slot_count).toBe(4);
  });
});

describe("uniqueWeaponId", () => {
  it("重複しなければそのまま返す", () => {
    expect(uniqueWeaponId("zaku_mg", ["heat_hawk"])).toBe("zaku_mg");
  });

  it("重複する場合は _2, _3 … と接尾辞を付ける", () => {
    expect(uniqueWeaponId("zaku_mg", ["zaku_mg"])).toBe("zaku_mg_2");
    expect(uniqueWeaponId("zaku_mg", ["zaku_mg", "zaku_mg_2"])).toBe("zaku_mg_3");
  });
});

describe("weaponSlotLabel", () => {
  it("Garage と同じく右腕・左腕・ラックN で表示する", () => {
    expect([0, 1, 2, 3].map(weaponSlotLabel)).toEqual(["右腕", "左腕", "ラック1", "ラック2"]);
  });
});

describe("武器マスターからの追加", () => {
  it("武器マスターの id / name / スペックをコピーする", () => {
    const weapon = masterWeaponToWeapon(masterWeapon, ["npc_weapon_abcd1234"]);
    expect(weapon).toMatchObject({ id: "zaku_mg", name: "Zaku Machine Gun", power: 120, cooldown_sec: 0.5 });
  });

  it("フォーム外の項目（cooldown_sec 等）は武器マスターの値で送信する", () => {
    const imported = masterWeaponToWeapon(masterWeapon, ["zaku_mg"]);
    const values = toNpcMobileSuitFormValues(npcSuit);
    values.mobile_suit.weapons.push(weaponToFormValues(imported));
    const payload = toNpcMobileSuitPayload(values, npcSuit, [imported]);
    const sent = payload.weapons![1];
    expect(sent.id).toBe("zaku_mg_2");
    expect(sent.weapon_type).toBe("RANGED");
    expect(sent.cooldown_sec).toBe(0.5);
    expect(sent.fire_arc_deg).toBe(45);
    expect(sent.max_ammo).toBe(60);
  });
});

// ============================================================
// マスターIDの記録とマスター値 (Issue #545)
// ============================================================

describe("マスターIDの記録", () => {
  it("機体の機体マスターIDをフォーム値に引き継ぐ", () => {
    const values = toNpcMobileSuitFormValues({ ...npcSuit, master_mobile_suit_id: "dom" });
    expect(values.mobile_suit.master_mobile_suit_id).toBe("dom");
    expect(values.mobile_suit.weapons[0].master_weapon_id).toBeNull();
  });

  it("武器マスターから追加した武器は、ID に接尾辞が付いても武器マスターIDを送る", () => {
    const imported = masterWeaponToWeapon(masterWeapon, ["zaku_mg"]);
    const values = toNpcMobileSuitFormValues(npcSuit);
    values.mobile_suit.weapons.push(weaponToFormValues(imported));
    const sent = toNpcMobileSuitPayload(values, npcSuit, [imported]).weapons![1];
    expect(sent.id).toBe("zaku_mg_2");
    expect(sent.master_weapon_id).toBe("zaku_mg");
  });

  it("機体マスターの取り込みでは、武器マスターにある武器だけ武器マスターIDを記録する", () => {
    const withTwoWeapons: MasterMobileSuit = {
      ...master,
      specs: {
        ...master.specs,
        weapons: [...master.specs.weapons, { id: "gelgoog_only", name: "Unique", power: 1, range: 1, accuracy: 1 }],
      },
    };
    const current = toNpcMobileSuitFormValues(npcSuit).mobile_suit;
    const next = masterToSpecValues(withTwoWeapons, current, new Set(["beam_rifle"]));
    expect(next.master_mobile_suit_id).toBe("gelgoog");
    expect(next.weapons.map((w) => w.master_weapon_id)).toEqual(["beam_rifle", null]);
  });
});

describe("masterMobileSuitValue", () => {
  it("スペックの項目と武器スロット数を返す", () => {
    expect(masterMobileSuitValue(master, "max_hp")).toBe(1100);
    expect(masterMobileSuitValue(master, "melee_aptitude")).toBe(1);
    expect(masterMobileSuitValue(master, "weapon_slot_count")).toBe(2);
  });

  it("機体マスターが無い（未記録・削除済み）ときは undefined", () => {
    expect(masterMobileSuitValue(undefined, "max_hp")).toBeUndefined();
  });
});

// ============================================================
// 武装持ち替えポリシー
// ============================================================

describe("武装持ち替えポリシー", () => {
  it("機体の設定値をフォームに読み込み、そのまま送る", () => {
    const suit: NpcMobileSuit = { ...npcSuit, tactics: { ...npcSuit.tactics, weapon_switch_policy: "NEVER" } };
    const values = toNpcMobileSuitFormValues(suit);
    expect(values.mobile_suit.tactics.weapon_switch_policy).toBe("NEVER");
    values.mobile_suit.tactics.weapon_switch_policy = "AGGRESSIVE";
    expect(toNpcMobileSuitPayload(values, suit).tactics?.weapon_switch_policy).toBe("AGGRESSIVE");
  });

  it("フォームで扱わない tactics のキーは保存時に残す", () => {
    const suit = { ...npcSuit, tactics: { ...npcSuit.tactics, custom_key: "kept" } } as NpcMobileSuit;
    const payload = toNpcMobileSuitPayload(toNpcMobileSuitFormValues(suit), suit);
    expect(payload.tactics).toMatchObject({ priority: "WEAKEST", custom_key: "kept" });
  });
});

// ============================================================
// 狙う部位配分
// ============================================================

const customAim = { HEAD: 0.3, TORSO: 0.3, RIGHT_ARM: 0.1, LEFT_ARM: 0.1, RIGHT_LEG: 0.1, LEFT_LEG: 0.1 };

function npcValuesWithAim(aim: Record<string, number>) {
  const values = toNpcMobileSuitFormValues(npcSuit);
  values.mobile_suit.weapons[0].aim_distribution = { ...DEFAULT_AIM_DISTRIBUTION_PERCENT, ...aim };
  return values;
}

describe("狙う部位配分", () => {
  it("未設定の武器は既定値を % で表示する", () => {
    const values = toNpcMobileSuitFormValues(npcSuit);
    expect(values.mobile_suit.weapons[0].aim_distribution).toEqual(DEFAULT_AIM_DISTRIBUTION_PERCENT);
  });

  it("武器の配分を % に変換して読み込み、割合に戻して送る", () => {
    const suit: NpcMobileSuit = {
      ...npcSuit,
      weapons: [{ ...npcSuit.weapons[0], aim_distribution: customAim }],
    };
    const values = toNpcMobileSuitFormValues(suit);
    expect(values.mobile_suit.weapons[0].aim_distribution).toMatchObject({ HEAD: 30, TORSO: 30, LEFT_LEG: 10 });
    expect(toNpcMobileSuitPayload(values, suit).weapons![0].aim_distribution).toEqual(customAim);
  });

  it("フォームで編集した配分を既存値より優先して送る", () => {
    const suit: NpcMobileSuit = {
      ...npcSuit,
      weapons: [{ ...npcSuit.weapons[0], aim_distribution: customAim }],
    };
    const values = toNpcMobileSuitFormValues(suit);
    values.mobile_suit.weapons[0].aim_distribution = { ...DEFAULT_AIM_DISTRIBUTION_PERCENT };
    expect(toNpcMobileSuitPayload(values, suit).weapons![0].aim_distribution).toMatchObject({ TORSO: 0.5 });
  });

  it("合計が 100% ±1% を外れる場合は配分の欄にエラー", () => {
    const result = npcMobileSuitSchema.safeParse(npcValuesWithAim({ HEAD: 12 }));
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toEqual(["mobile_suit", "weapons", 0, "aim_distribution"]);
    expect(result.error?.issues[0].message).toBe("Total must be 100% (current: 102%)");
  });

  it("合計が許容誤差内なら通過する", () => {
    expect(npcMobileSuitSchema.safeParse(npcValuesWithAim({ HEAD: 10.5, TORSO: 50.4 })).success).toBe(true);
  });

  it("負の値はエラー", () => {
    const result = npcMobileSuitSchema.safeParse(npcValuesWithAim({ HEAD: -10, TORSO: 70 }));
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toEqual(["mobile_suit", "weapons", 0, "aim_distribution", "HEAD"]);
  });

  it("欠損部位に配分が残っていても通過する", () => {
    const values = npcValuesWithAim({});
    values.mobile_suit.missing_parts = ["HEAD"];
    expect(npcMobileSuitSchema.safeParse(values).success).toBe(true);
  });
});
