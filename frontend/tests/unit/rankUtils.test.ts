import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, it, expect } from "vitest";
import {
  enrichMobileSuit,
  getMobileSuitRanks,
  getWeaponPowerRank,
} from "@/utils/rankUtils";
import { MobileSuit } from "@/types/battle";

type Threshold = { rank: string; min: number };

/** バックエンドの閾値（API の hp_rank 等の算出元） */
const backendThresholds: Record<string, Threshold[]> = JSON.parse(
  readFileSync(
    path.join(__dirname, "../../../backend/data/master/thresholds.json"),
    "utf-8",
  ),
);

/** バックエンドの get_rank() と同じ手順でランクを求める */
function backendRank(stat: string, value: number): string {
  for (const entry of backendThresholds[stat]) {
    if (value >= entry.min) return entry.rank;
  }
  return "E";
}

/** バトル結果の ms_snapshot と同じく、ランクを含まない機体データ */
const snapshot = (overrides: Partial<MobileSuit> = {}): MobileSuit => ({
  id: "ms-1",
  name: "Gundam",
  max_hp: 1200,
  current_hp: 1200,
  armor: 70,
  mobility: 1.6,
  position: { x: 0, y: 0, z: 0 },
  weapons: [],
  side: "PLAYER",
  tactics: { priority: "CLOSEST", range: "BALANCED" },
  ...overrides,
});

describe("getMobileSuitRanks", () => {
  it("ランクが無い機体は、バックエンドと同じ閾値で値から算出する", () => {
    expect(getMobileSuitRanks(snapshot())).toEqual({
      hp: "B",
      armor: "B",
      mobility: "A",
    });
  });

  it.each([
    ["hp", "max_hp"],
    ["armor", "armor"],
    ["mobility", "mobility"],
  ] as const)("%s の境界値がバックエンドの算出と一致する", (stat, field) => {
    for (const { min } of backendThresholds[stat]) {
      for (const value of [min, min - 0.01]) {
        const ranks = getMobileSuitRanks(snapshot({ [field]: value }));
        expect(ranks[stat]).toBe(backendRank(stat, value));
      }
    }
  });

  it("API のランクがあればそれを使う", () => {
    const ms = snapshot({ hp_rank: "S", armor_rank: "E", mobility_rank: "D" });
    expect(getMobileSuitRanks(ms)).toEqual({
      hp: "S",
      armor: "E",
      mobility: "D",
    });
  });

  it("Garage の表示（enrichMobileSuit）と同じランクになる", () => {
    const ms = snapshot({ max_hp: 650, armor: 100, mobility: 0.95 });
    const { display } = enrichMobileSuit(ms);
    expect(getMobileSuitRanks(ms)).toEqual({
      hp: display.hp.rank,
      armor: display.armor.rank,
      mobility: display.mobility.rank,
    });
  });
});

describe("getWeaponPowerRank", () => {
  it("ランクが無い武器は、バックエンドと同じ閾値で威力から算出する", () => {
    for (const { min } of backendThresholds.weapon_power) {
      expect(getWeaponPowerRank({ power: min })).toBe(
        backendRank("weapon_power", min),
      );
    }
  });

  it("API のランクがあればそれを使う", () => {
    expect(getWeaponPowerRank({ power: 10, power_rank: "S" })).toBe("S");
  });
});
