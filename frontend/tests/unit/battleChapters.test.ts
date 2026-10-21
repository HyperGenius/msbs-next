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

/** 僚機・第三者を含む多人数戦用のデータ */
const TEAM_PLAYER = { ...PLAYER, team_id: "team-a" };
const ally: MobileSuit = { ...enemy, id: "ally-001", name: "Gundam", side: "PLAYER", team_id: "team-a" };
const other: MobileSuit = { ...enemy, id: "other-001", name: "Gelgoog", team_id: "team-c" };

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

  it("damageが0のコンボでもdetailは「-0」になる（falsy値の取り違え回避）", () => {
    const logs = [makeLog({ action_type: "MELEE_COMBO", target_id: enemy.id, combo_count: 1, damage: 0 })];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters[0].detail).toBe("-0");
  });

  it("damageが0のクリティカルでもdetailは「-0」になる（falsy値の取り違え回避）", () => {
    const logs = [makeLog({ action_type: "ATTACK", target_id: enemy.id, is_crit: true, damage: 0 })];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters[0].detail).toBe("-0");
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

  it("自機による敵機の撃破をDESTROYED_ENEMYチャプターとして抽出する", () => {
    const logs = [
      makeLog({ action_type: "ATTACK", target_id: enemy.id, damage: 120 }),
      makeLog({ actor_id: enemy.id, action_type: "DESTROYED", message: "爆散した" }),
    ];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters).toHaveLength(1);
    expect(chapters[0].kind).toBe("DESTROYED_ENEMY");
    expect(chapters[0].label).toBe("Zaku IIを撃破");
  });

  it("格闘コンボでの撃破もDESTROYED_ENEMYチャプターとして抽出する", () => {
    const logs = [
      makeLog({ action_type: "MELEE_COMBO", target_id: enemy.id, combo_count: 2, damage: 200 }),
      makeLog({ actor_id: enemy.id, action_type: "DESTROYED" }),
    ];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters.map((c) => c.kind)).toEqual(["COMBO", "DESTROYED_ENEMY"]);
  });

  it("僚機による敵機の撃破をDESTROYED_ENEMYチャプターとして抽出する", () => {
    const logs = [
      makeLog({ actor_id: ally.id, action_type: "ATTACK", target_id: enemy.id, damage: 120 }),
      makeLog({ actor_id: enemy.id, action_type: "DESTROYED" }),
    ];
    const chapters = computeBattleChapters(logs, TEAM_PLAYER, [ally, enemy]);
    expect(chapters.map((c) => [c.kind, c.label])).toEqual([["DESTROYED_ENEMY", "Zaku IIを撃破"]]);
  });

  it("第三者同士の撃破はチャプターにならない", () => {
    const logs = [
      makeLog({ actor_id: other.id, action_type: "ATTACK", target_id: enemy.id, damage: 120 }),
      makeLog({ actor_id: enemy.id, action_type: "DESTROYED" }),
    ];
    expect(computeBattleChapters(logs, TEAM_PLAYER, [ally, enemy, other])).toHaveLength(0);
  });

  it("撃破者を特定できない撃破ログはチャプターにならない", () => {
    const logs = [
      // 直前のログが攻撃でない
      makeLog({ action_type: "MOVE" }),
      makeLog({ actor_id: enemy.id, action_type: "DESTROYED" }),
      // 直前の攻撃が別の対象へのもの
      makeLog({ action_type: "ATTACK", target_id: other.id, damage: 50 }),
      makeLog({ actor_id: enemy.id, action_type: "DESTROYED" }),
    ];
    expect(computeBattleChapters(logs, PLAYER, [enemy, other])).toHaveLength(0);
    // 先頭の撃破ログ
    expect(computeBattleChapters([makeLog({ actor_id: enemy.id, action_type: "DESTROYED" })], PLAYER, [enemy])).toHaveLength(0);
  });

  it("僚機の撃破をDESTROYED_ALLYチャプターとして抽出する（「〇〇を撃破」とは出さない）", () => {
    const logs = [
      makeLog({ actor_id: enemy.id, action_type: "ATTACK", target_id: ally.id, damage: 120 }),
      makeLog({ actor_id: ally.id, action_type: "DESTROYED" }),
    ];
    const chapters = computeBattleChapters(logs, TEAM_PLAYER, [ally, enemy]);
    expect(chapters.map((c) => [c.kind, c.label])).toEqual([["DESTROYED_ALLY", "僚機Gundamが撃破された"]]);
  });

  it("ソロ参加（team_idがnull）では、team_idを持つ他機を僚機と判定しない", () => {
    // 保存データ上、ソロ参加の enemies_info にはシミュレーターが自動付与した team_id が入る
    const soloEnemy: MobileSuit = { ...enemy, team_id: enemy.id };
    const nullTeamEnemy: MobileSuit = { ...other, team_id: null };
    const logs = [
      makeLog({ action_type: "ATTACK", target_id: soloEnemy.id, damage: 120 }),
      makeLog({ actor_id: soloEnemy.id, action_type: "DESTROYED" }),
      makeLog({ action_type: "ATTACK", target_id: nullTeamEnemy.id, damage: 120 }),
      makeLog({ actor_id: nullTeamEnemy.id, action_type: "DESTROYED" }),
    ];
    const chapters = computeBattleChapters(logs, { ...PLAYER, team_id: null }, [soloEnemy, nullTeamEnemy]);
    expect(chapters.map((c) => [c.kind, c.label])).toEqual([
      ["DESTROYED_ENEMY", "Zaku IIを撃破"],
      ["DESTROYED_ENEMY", "Gelgoogを撃破"],
    ]);
  });

  it("自機の撃破をDESTROYED_SELFチャプターとして抽出する", () => {
    const logs = [makeLog({ actor_id: PLAYER.id, action_type: "DESTROYED", message: "爆散した" })];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters).toHaveLength(1);
    expect(chapters[0].kind).toBe("DESTROYED_SELF");
  });

  it("バトルに参加していないユニットの撃破ログはチャプターにならない", () => {
    const logs = [
      makeLog({ action_type: "ATTACK", target_id: "unrelated-999", damage: 120 }),
      makeLog({ actor_id: "unrelated-999", action_type: "DESTROYED" }),
    ];
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

  it("自機の仕切り直しをDISENGAGEチャプターとして抽出する", () => {
    const logs = [makeLog({ action_type: "DISENGAGE", target_id: enemy.id })];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters).toHaveLength(1);
    expect(chapters[0].kind).toBe("DISENGAGE");
    expect(chapters[0].label).toBe("Zaku IIから仕切り直し");
  });

  it("敵機の仕切り直しはチャプターにならない", () => {
    const logs = [makeLog({ actor_id: enemy.id, action_type: "DISENGAGE", target_id: PLAYER.id })];
    expect(computeBattleChapters(logs, PLAYER, [enemy])).toHaveLength(0);
  });

  it("自機が絡む鍔迫り合いをCLASHチャプターとして抽出する", () => {
    const logs = [
      makeLog({ action_type: "MELEE_CLASH", target_id: enemy.id }),
      makeLog({ action_type: "MELEE_CLASH", actor_id: enemy.id, target_id: PLAYER.id }),
    ];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters.map((c) => [c.kind, c.label])).toEqual([
      ["CLASH", "Zaku IIと鍔迫り合い"],
      ["CLASH", "Zaku IIと鍔迫り合い"],
    ]);
  });

  it("自機が絡まない鍔迫り合いはチャプターにならない", () => {
    const logs = [makeLog({ actor_id: enemy.id, action_type: "MELEE_CLASH", target_id: "ally-001" })];
    expect(computeBattleChapters(logs, PLAYER, [enemy])).toHaveLength(0);
  });

  it("複数種のチャプターをログの時系列順のまま返す", () => {
    const logs = [
      makeLog({ timestamp: 1, action_type: "DETECTION", target_id: enemy.id }),
      makeLog({ timestamp: 5, action_type: "MELEE_COMBO", target_id: enemy.id, combo_count: 2, damage: 100 }),
      makeLog({ timestamp: 8, action_type: "ATTACK", target_id: enemy.id, damage: 80 }),
      makeLog({ timestamp: 8, actor_id: enemy.id, action_type: "DESTROYED" }),
    ];
    const chapters = computeBattleChapters(logs, PLAYER, [enemy]);
    expect(chapters.map((c) => c.kind)).toEqual(["DETECTION", "COMBO", "DESTROYED_ENEMY"]);
  });
});
