/* frontend/tests/unit/weaponAccuracySummary.test.ts */
import { describe, it, expect } from "vitest";
import { computeWeaponAccuracySummary } from "@/hooks/useWeaponAccuracySummary";
import { BattleLog } from "@/types/battle";

const PLAYER_ID = "player-001";

function makeLog(overrides: Partial<BattleLog> = {}): BattleLog {
  return {
    timestamp: 1,
    actor_id: PLAYER_ID,
    action_type: "ATTACK",
    message: "攻撃した",
    position_snapshot: { x: 0, y: 0, z: 0 },
    weapon_name: "ビームライフル",
    ...overrides,
  };
}

describe("computeWeaponAccuracySummary", () => {
  it("playerIdがnullのときは空配列を返す", () => {
    expect(computeWeaponAccuracySummary(null, [makeLog()])).toEqual([]);
  });

  it("ATTACK/MISSの件数から命中率を算出する", () => {
    const logs = [
      makeLog({ action_type: "ATTACK" }),
      makeLog({ action_type: "ATTACK" }),
      makeLog({ action_type: "MISS" }),
    ];
    const result = computeWeaponAccuracySummary(PLAYER_ID, logs);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({ weaponName: "ビームライフル", hits: 2, attempts: 3, accuracy: 2 / 3 });
  });

  it("MELEE_COMBOはHIT扱いになる", () => {
    const logs = [makeLog({ action_type: "MELEE_COMBO" })];
    const result = computeWeaponAccuracySummary(PLAYER_ID, logs);
    expect(result[0]).toMatchObject({ hits: 1, attempts: 1 });
  });

  it("equippedWeaponNamesに渡した未使用武器は0/0・accuracy nullで一覧に含まれる（--%表示用）", () => {
    const result = computeWeaponAccuracySummary(PLAYER_ID, [], ["ハイパーバズーカ"]);
    expect(result).toEqual([{ weaponName: "ハイパーバズーカ", hits: 0, attempts: 0, accuracy: null }]);
  });

  it("equippedWeaponNames未指定でログが空なら空配列を返す", () => {
    const result = computeWeaponAccuracySummary(PLAYER_ID, []);
    expect(result).toEqual([]);
  });

  it("weapon_name未指定の格闘攻撃は「格闘」として集計される", () => {
    const logs = [makeLog({ action_type: "MELEE_COMBO", weapon_name: undefined })];
    const result = computeWeaponAccuracySummary(PLAYER_ID, logs);
    expect(result[0].weaponName).toBe("格闘");
  });

  it("敵の攻撃ログ（actor_idが自機以外）は集計に含めない", () => {
    const logs = [makeLog({ actor_id: "enemy-001", action_type: "ATTACK" })];
    expect(computeWeaponAccuracySummary(PLAYER_ID, logs)).toEqual([]);
  });

  it("武器ごとに別々に集計する", () => {
    const logs = [
      makeLog({ weapon_name: "ビームライフル", action_type: "ATTACK" }),
      makeLog({ weapon_name: "バルカン", action_type: "MISS" }),
    ];
    const result = computeWeaponAccuracySummary(PLAYER_ID, logs);
    expect(result).toHaveLength(2);
    const rifle = result.find((r) => r.weaponName === "ビームライフル");
    const vulcan = result.find((r) => r.weaponName === "バルカン");
    expect(rifle).toMatchObject({ hits: 1, attempts: 1, accuracy: 1 });
    expect(vulcan).toMatchObject({ hits: 0, attempts: 1, accuracy: 0 });
  });

  it("ATTACK/MISS/MELEE_COMBO以外のaction_type（DETECTION等）は集計対象外", () => {
    const logs = [makeLog({ action_type: "DETECTION", target_id: "enemy-001" })];
    expect(computeWeaponAccuracySummary(PLAYER_ID, logs)).toEqual([]);
  });
});
