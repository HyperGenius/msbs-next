import { describe, it, expect } from "vitest";
import { missionMasterError, referencesMaster } from "@/lib/localSim/missionEdit";
import type { LocalSimMissionMaster, LocalSimMissionUnit } from "@/types/localSim";

const inline: LocalSimMissionUnit = {
  name: "ザクII",
  max_hp: 80,
  armor: 5,
  mobility: 1.2,
  weapon: {
    id: "mg",
    name: "MG",
    power: 15,
    range: 400,
    accuracy: 70,
    weapon_type: "RANGED",
    is_melee: false,
    fire_arc_deg: 30,
  },
  role: null,
  squad_id: null,
};

function master(enemies: LocalSimMissionUnit[]): LocalSimMissionMaster {
  return { allies_config: null, enemy_config: { enemies }, objective: null };
}

describe("referencesMaster", () => {
  it("機体マスターかエースを参照する機体を見分ける", () => {
    expect(referencesMaster({ master_mobile_suit_id: "gouf" })).toBe(true);
    expect(referencesMaster({ ace_id: "ace_char_aznable" })).toBe(true);
    expect(referencesMaster(inline)).toBe(false);
  });
});

describe("missionMasterError", () => {
  it("参照する機体は直書きの性能が無くても通す", () => {
    expect(missionMasterError(master([{ master_mobile_suit_id: "gouf" }, { ace_id: "ace_char_aznable", current_hp_ratio: 1 }]))).toBeNull();
  });

  it("参照する機体の HP の割合は 0 より大きく 1 以下にする", () => {
    for (const ratio of [0, 1.5, NaN]) {
      expect(missionMasterError(master([{ master_mobile_suit_id: "gouf", current_hp_ratio: ratio }]))).toBe("作戦の機体「gouf」の値が不正です。");
    }
  });

  it("直書きの機体は性能と武器を確かめる", () => {
    expect(missionMasterError(master([inline]))).toBeNull();
    expect(missionMasterError(master([{ ...inline, max_hp: 0 }]))).toBe("作戦の機体「ザクII」の値が不正です。");
    expect(missionMasterError(master([{ ...inline, weapon: undefined }]))).toBe("作戦の機体「ザクII」の値が不正です。");
  });
});
