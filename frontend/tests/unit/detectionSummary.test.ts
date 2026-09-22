/* frontend/tests/unit/detectionSummary.test.ts */
import { describe, it, expect } from "vitest";
import { computeDetectionSummary } from "@/hooks/useDetectionSummary";
import { BattleLog } from "@/types/battle";
import { MobileSuit } from "@/types/mobileSuit";

const PLAYER_ID = "player-001";

function makeEnemy(id: string): MobileSuit {
  return {
    id,
    name: id,
    max_hp: 400,
    current_hp: 400,
    armor: 0,
    mobility: 1,
    position: { x: 0, y: 0, z: 0 },
    weapons: [],
    side: "ENEMY",
    tactics: { priority: "CLOSEST", range: "RANGED" },
  };
}

function makeLog(overrides: Partial<BattleLog> = {}): BattleLog {
  return {
    timestamp: 1,
    actor_id: PLAYER_ID,
    action_type: "DETECTION",
    message: "発見した",
    position_snapshot: { x: 0, y: 0, z: 0 },
    ...overrides,
  };
}

describe("computeDetectionSummary", () => {
  it("自機が索敵に成功した敵機のユニークな数をcapturedとして返す", () => {
    const enemies = [makeEnemy("enemy-001"), makeEnemy("enemy-002"), makeEnemy("enemy-003")];
    const logs = [
      makeLog({ target_id: "enemy-001" }),
      makeLog({ target_id: "enemy-001" }), // 同じ敵を複数回発見しても重複カウントしない
      makeLog({ target_id: "enemy-002" }),
    ];
    const result = computeDetectionSummary(PLAYER_ID, logs, enemies);
    expect(result).toEqual({ captured: 2, total: 3 });
  });

  it("敵起点の索敵ログ（自機が発見された側）はcapturedに含めない", () => {
    const enemies = [makeEnemy("enemy-001")];
    const logs = [makeLog({ actor_id: "enemy-001", action_type: "DETECTION", target_id: PLAYER_ID })];
    const result = computeDetectionSummary(PLAYER_ID, logs, enemies);
    expect(result).toEqual({ captured: 0, total: 1 });
  });

  it("playerIdがnullのときはcaptured 0、totalは敵機数を返す", () => {
    const enemies = [makeEnemy("enemy-001"), makeEnemy("enemy-002")];
    expect(computeDetectionSummary(null, [], enemies)).toEqual({ captured: 0, total: 2 });
  });

  it("DETECTION以外のaction_typeは集計対象外", () => {
    const enemies = [makeEnemy("enemy-001")];
    const logs = [makeLog({ action_type: "ATTACK", target_id: "enemy-001" })];
    const result = computeDetectionSummary(PLAYER_ID, logs, enemies);
    expect(result.captured).toBe(0);
  });
});
