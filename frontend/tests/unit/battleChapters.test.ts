/* frontend/tests/unit/battleChapters.test.ts */
import { describe, it, expect } from "vitest";
import { computeBattleChapters } from "@/components/BattleViewer/hooks/useBattleChapters";
import { BattleLog } from "@/types/battle";
import { MobileSuit } from "@/types/mobileSuit";

const PLAYER = { id: "player-001", name: "GM改" };

const enemy: MobileSuit = {
  id: "enemy-001",
  name: "Zaku II",
  max_hp: 400,
  current_hp: 400,
  armor: 0,
  mobility: 1,
  position: { x: 0, y: 0, z: 0 },
  weapons: [],
  side: "ENEMY",
  tactics: { priority: "CLOSEST", range: "RANGED" },
};

function makeLog(overrides: Partial<BattleLog> = {}): BattleLog {
  return {
    timestamp: 1,
    actor_id: PLAYER.id,
    action_type: "ATTACK",
    message: "攻撃した",
    position_snapshot: { x: 0, y: 0, z: 0 },
    ...overrides,
  };
}

describe("computeBattleChapters", () => {
  it("自機の格闘コンボをCOMBOチャプターとして抽出する", () => {
    const logs = [
      makeLog({ action_type: "MELEE_COMBO", target_id: enemy.id, combo_count: 3, damage: 240 }),
    ];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters).toHaveLength(1);
    expect(chapters[0].kind).toBe("COMBO");
    expect(chapters[0].label).toBe("3HIT格闘コンボ");
    expect(chapters[0].detail).toBe("-240");
  });

  it("is_crit=trueのATTACKをCRITICALチャプターとして抽出する", () => {
    const logs = [
      makeLog({ action_type: "ATTACK", target_id: enemy.id, is_crit: true, damage: 320, weapon_name: "ビームライフル" }),
    ];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters).toHaveLength(1);
    expect(chapters[0].kind).toBe("CRITICAL");
    expect(chapters[0].label).toBe("ビームライフル クリティカルヒット");
  });

  it("is_crit=falseのATTACKはチャプターにならない", () => {
    const logs = [makeLog({ action_type: "ATTACK", target_id: enemy.id, is_crit: false, damage: 50 })];
    expect(computeBattleChapters(logs, PLAYER, [enemy])).toHaveLength(0);
  });

  it("通常のATTACK/MISSはチャプターにならない（読むログではなくジャンプ先のみ）", () => {
    const logs = [
      makeLog({ action_type: "ATTACK", target_id: enemy.id, damage: 30 }),
      makeLog({ action_type: "MISS", target_id: enemy.id }),
    ];
    expect(computeBattleChapters(logs, PLAYER, [enemy])).toHaveLength(0);
  });

  it("敵機の撃破をDESTROYED_ENEMYチャプターとして抽出する", () => {
    const logs = [makeLog({ actor_id: enemy.id, action_type: "DESTROYED", message: "爆散した" })];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters).toHaveLength(1);
    expect(chapters[0].kind).toBe("DESTROYED_ENEMY");
    expect(chapters[0].label).toBe("Zaku IIを撃破");
  });

  it("自機の撃破をDESTROYED_SELFチャプターとして抽出する", () => {
    const logs = [makeLog({ actor_id: PLAYER.id, action_type: "DESTROYED", message: "爆散した" })];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters).toHaveLength(1);
    expect(chapters[0].kind).toBe("DESTROYED_SELF");
  });

  it("バトルに参加していないユニットの撃破ログはチャプターにならない", () => {
    const logs = [makeLog({ actor_id: "unrelated-999", action_type: "DESTROYED" })];
    expect(computeBattleChapters(logs, PLAYER, [enemy])).toHaveLength(0);
  });

  it("自機起点の索敵成功をDETECTIONチャプターとして抽出する", () => {
    const logs = [makeLog({ action_type: "DETECTION", target_id: enemy.id })];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters).toHaveLength(1);
    expect(chapters[0].kind).toBe("DETECTION");
    expect(chapters[0].label).toBe("Zaku IIを発見");
  });

  it("敵機起点の索敵ログ（自機が発見された側）はチャプターにならない", () => {
    const logs = [makeLog({ actor_id: enemy.id, action_type: "DETECTION", target_id: PLAYER.id })];
    expect(computeBattleChapters(logs, PLAYER, [enemy])).toHaveLength(0);
  });

  it("複数種のチャプターをログの時系列順のまま返す", () => {
    const logs = [
      makeLog({ timestamp: 1, action_type: "DETECTION", target_id: enemy.id }),
      makeLog({ timestamp: 5, action_type: "MELEE_COMBO", target_id: enemy.id, combo_count: 2, damage: 100 }),
      makeLog({ timestamp: 9, actor_id: enemy.id, action_type: "DESTROYED" }),
    ];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters.map((c) => c.kind)).toEqual(["DETECTION", "COMBO", "DESTROYED_ENEMY"]);
  });
});
