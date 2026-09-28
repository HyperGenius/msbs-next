import { describe, it, expect } from "vitest";
import {
  environmentFormSchema,
  formatJstDate,
  formatMinovskyRange,
  setTerrainGrade,
  sortByRotation,
  terrainAdaptabilitySchema,
  theaterFormSchema,
  toEnvironmentFormValues,
  toTheaterFormValues,
  toTheaterPayload,
  unmanagedTerrainKeys,
} from "@/lib/theater";
import { masterMobileSuitSchema } from "@/components/admin/MobileSuitEditForm";
import { MasterEnvironment, MasterTheater } from "@/types/admin";

const FOREST: MasterEnvironment = {
  id: "FOREST",
  name: "森林",
  description: "",
  sensor_range_multiplier: 0.8,
  ranged_accuracy_penalty: 0.2,
  ranged_penalty_ref_distance: 400,
  default_obstacle_density: "DENSE",
  default_terrain_grade: "A",
  viewer_preset: "FOREST",
};
const SPACE: MasterEnvironment = { ...FOREST, id: "SPACE", name: "宇宙" };

const SOLOMON: MasterTheater = {
  id: "solomon",
  name: "ソロモン宙域",
  environment_id: "SPACE",
  base_minovsky: 0.35,
  minovsky_variance: 0.15,
  obstacle_density: null,
  hint: "",
  description: "",
  rotation_order: 10,
  is_active: true,
};
const JUNGLE: MasterTheater = {
  ...SOLOMON,
  id: "southeast_asia_jungle",
  environment_id: "FOREST",
  rotation_order: 20,
};

describe("environmentFormSchema", () => {
  const valid = { ...toEnvironmentFormValues(null), id: "DESERT", name: "砂漠" };

  it("新規作成の初期値に ID と名前を入れれば通る", () => {
    expect(environmentFormSchema.safeParse(valid).success).toBe(true);
  });

  it.each([
    { id: "desert" },
    { id: "DES-ERT" },
    { name: "" },
    { sensor_range_multiplier: 0 },
    { sensor_range_multiplier: 1.1 },
    { ranged_accuracy_penalty: -0.1 },
    { ranged_accuracy_penalty: 1.1 },
    { ranged_penalty_ref_distance: 0 },
    { default_obstacle_density: "HEAVY" },
    { default_terrain_grade: "E" },
    { viewer_preset: "DESERT" },
  ])("backend と同じ規則で拒否する: %o", (override) => {
    expect(environmentFormSchema.safeParse({ ...valid, ...override }).success).toBe(false);
  });
});

describe("theaterFormSchema", () => {
  const valid = { ...toTheaterFormValues(null), id: "odessa", name: "オデッサ", environment_id: "SPACE" };

  it("新規作成の初期値に ID・名前・環境を入れれば通る", () => {
    expect(theaterFormSchema.safeParse(valid).success).toBe(true);
  });

  it.each([
    { id: "Odessa" },
    { environment_id: "" },
    { base_minovsky: 1.1 },
    { minovsky_variance: 0.6 },
    { rotation_order: 1.5 },
  ])("範囲外の値を拒否する: %o", (override) => {
    expect(theaterFormSchema.safeParse({ ...valid, ...override }).success).toBe(false);
  });
});

describe("toTheaterFormValues / toTheaterPayload", () => {
  it("新規作成の順番は既存の最大値 + 10", () => {
    expect(toTheaterFormValues(null, [SOLOMON, JUNGLE]).rotation_order).toBe(30);
    expect(toTheaterFormValues(null, []).rotation_order).toBe(10);
  });

  it("障害物密度の null はフォームで空文字になり、送信時に null に戻る", () => {
    const values = toTheaterFormValues(SOLOMON);
    expect(values.obstacle_density).toBe("");
    expect(toTheaterPayload(values)).toEqual(SOLOMON);
    expect(toTheaterPayload({ ...values, obstacle_density: "DENSE" }).obstacle_density).toBe("DENSE");
  });
});

describe("sortByRotation", () => {
  it("順番、同じなら ID の昇順に並べる", () => {
    const tie = { ...SOLOMON, id: "a_baoa_qu", rotation_order: 20 };
    expect(sortByRotation([JUNGLE, tie, SOLOMON]).map((t) => t.id)).toEqual([
      "solomon",
      "a_baoa_qu",
      "southeast_asia_jungle",
    ]);
  });
});

describe("formatMinovskyRange", () => {
  it("基準値 ± 揺らぎ幅を 0〜100% に収めて表示する", () => {
    expect(formatMinovskyRange(SOLOMON)).toBe("20%〜50%");
    expect(formatMinovskyRange({ base_minovsky: 0.9, minovsky_variance: 0.3 })).toBe("60%〜100%");
    expect(formatMinovskyRange({ base_minovsky: 0.1, minovsky_variance: 0.3 })).toBe("0%〜40%");
  });
});

describe("formatJstDate", () => {
  it("UTC の開催予定時刻を JST の日付と曜日にする", () => {
    expect(formatJstDate("2026-10-02T12:00:00Z")).toBe("10/2(金)");
    // 15:00 UTC は JST の翌日。
    expect(formatJstDate("2026-10-02T15:00:00Z")).toBe("10/3(土)");
  });
});

describe("地形適正", () => {
  it("ランクを選ぶとキーを設定し、「既定」ではキーを消す", () => {
    const terrain = { SPACE: "A", GROUND: "B" };
    expect(setTerrainGrade(terrain, "FOREST", "C")).toEqual({ SPACE: "A", GROUND: "B", FOREST: "C" });
    expect(setTerrainGrade(terrain, "SPACE", "")).toEqual({ GROUND: "B" });
    expect(terrain).toEqual({ SPACE: "A", GROUND: "B" });
  });

  it("環境タイプのマスターに無いキーを返す", () => {
    expect(unmanagedTerrainKeys([SPACE, FOREST], { UNDERWATER: "C", SPACE: "A", GROUND: "B" })).toEqual([
      "GROUND",
      "UNDERWATER",
    ]);
  });

  it("S〜D 以外のランクを拒否する", () => {
    expect(terrainAdaptabilitySchema.safeParse({ SPACE: "S", FOREST: "D" }).success).toBe(true);
    expect(terrainAdaptabilitySchema.safeParse({ SPACE: "E" }).success).toBe(false);
  });

  it("機体マスターのフォームで地形適正を検証する", () => {
    const base = {
      id: "zaku",
      name: "Zaku",
      name_ja: "",
      model_number: "",
      price: 100,
      faction: "",
      description: "",
      weapon_slot_count: 1,
      beam_generator_lv: 0,
      flavor_text: "",
      specs: {
        max_hp: 800,
        armor: 50,
        mobility: 1,
        sensor_range: 500,
        beam_resistance: 0,
        physical_resistance: 0,
        melee_aptitude: 1,
        shooting_aptitude: 1,
        accuracy_bonus: 0,
        evasion_bonus: 0,
        acceleration_bonus: 1,
        turning_bonus: 1,
        weapons: [
          {
            id: "mg",
            name: "MG",
            power: 100,
            range: 400,
            accuracy: 60,
            type: "PHYSICAL" as const,
            optimal_range: 300,
            decay_rate: 0.08,
            is_melee: false,
          },
        ],
        terrain_adaptability: { FOREST: "B" },
      },
      blueprint: { is_standard_issue: true, duplicate_credit_value: null, tech_requirements: [] },
    };
    expect(masterMobileSuitSchema.safeParse(base).success).toBe(true);
    const invalid = { ...base, specs: { ...base.specs, terrain_adaptability: { FOREST: "X" } } };
    expect(masterMobileSuitSchema.safeParse(invalid).success).toBe(false);
  });
});
