/* frontend/tests/unit/playerDestruction.test.ts */
import { describe, it, expect } from "vitest";
import {
  findPlayerDestroyedAt,
  getPlaybackLimit,
  PLAYER_DESTROYED_GRACE_S,
} from "@/components/BattleViewer/utils/playerDestruction";
import { BattleLog } from "@/types/battle";

function makeLog(overrides: Partial<BattleLog>): BattleLog {
  return {
    timestamp: 1,
    actor_id: "player-001",
    action_type: "ATTACK",
    message: "",
    position_snapshot: { x: 0, y: 0, z: 0 },
    ...overrides,
  };
}

describe("findPlayerDestroyedAt", () => {
  it("自機の撃破ログの時刻を返す", () => {
    const logs = [makeLog({ timestamp: 2 }), makeLog({ timestamp: 5, action_type: "DESTROYED" })];
    expect(findPlayerDestroyedAt(logs, "player-001")).toBe(5);
  });

  it("敵機の撃破ログは無視する", () => {
    const logs = [makeLog({ timestamp: 3, action_type: "DESTROYED", actor_id: "enemy-001" })];
    expect(findPlayerDestroyedAt(logs, "player-001")).toBeNull();
  });
});

describe("getPlaybackLimit", () => {
  it("撃破されていなければログ末尾までを上限にする", () => {
    expect(getPlaybackLimit(20, null)).toBe(20);
  });

  it("撃破時刻に猶予秒数を足した時刻を上限にする", () => {
    expect(getPlaybackLimit(20, 5)).toBe(5 + PLAYER_DESTROYED_GRACE_S);
  });

  it("猶予を足してもログ末尾を超えない", () => {
    expect(getPlaybackLimit(6, 5)).toBe(6);
  });
});
