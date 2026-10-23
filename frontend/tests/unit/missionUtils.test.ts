import { describe, it, expect } from "vitest";
import {
  describeObjective,
  formatObjectiveProgress,
  getObjectiveSummary,
} from "@/utils/missionName";
import { getRecentRetreatNotices, getRetreatedUnitIds } from "@/components/BattleViewer/utils/retreat";
import type { AvailableMission, BattleLog } from "@/types/battle";

const mission = (over: Partial<AvailableMission> = {}): AvailableMission => ({
  id: 4,
  name: "撤退支援",
  description: "",
  difficulty: 2,
  objective_type: "RETREAT_SUPPORT",
  objective_params: { required: 2 },
  environment: "FOREST",
  ally_count: 3,
  enemy_count: 4,
  ...over,
});

const retreatLog = (timestamp: number, actor: string): BattleLog =>
  ({
    timestamp,
    actor_id: actor,
    action_type: "RETREAT_COMPLETE",
    position_snapshot: { x: 1, y: 0, z: 2 },
  }) as BattleLog;

describe("describeObjective", () => {
  it("撤退支援は友軍の数と必要数を含む", () => {
    expect(describeObjective(mission())).toBe("友軍を3機中2機以上、撤退ポイントまで逃がす");
  });
  it("殲滅は敵を殲滅する", () => {
    expect(describeObjective(mission({ objective_type: "ANNIHILATION", objective_params: {} }))).toBe(
      "敵を殲滅する",
    );
  });
});

describe("getObjectiveSummary", () => {
  it("作戦IDが無いバトルロイヤルは null", () => {
    expect(
      getObjectiveSummary({ mission_id: null, objective_status: "SUCCESS" }),
    ).toBeNull();
  });
  it("作戦の結果が無い戦歴は null", () => {
    expect(getObjectiveSummary({ mission_id: 4, objective_status: null })).toBeNull();
  });
  it("作戦の結果と内訳をまとめる", () => {
    expect(
      getObjectiveSummary({
        mission_id: 4,
        objective_status: "SUCCESS",
        objective_progress: 2,
        objective_required: 2,
        objective_detail: { total: 3, lost: 1 },
      }),
    ).toEqual({ status: "SUCCESS", progress: 2, required: 2, total: 3, lost: 1 });
  });
});

describe("formatObjectiveProgress", () => {
  it("離脱数を出す。数えない目標は null", () => {
    expect(formatObjectiveProgress(2, 3)).toBe("離脱 2/3");
    expect(formatObjectiveProgress(null, 3)).toBeNull();
    expect(formatObjectiveProgress(1, undefined)).toBeNull();
  });
});

describe("retreat log helpers", () => {
  const logs = [retreatLog(5, "a"), retreatLog(9, "b")];
  it("指定時刻までに離脱したユニットを返す", () => {
    expect([...getRetreatedUnitIds(logs, 6)]).toEqual(["a"]);
    expect([...getRetreatedUnitIds(logs, 10)].sort()).toEqual(["a", "b"]);
  });
  it("直近の離脱だけ通知に出す", () => {
    expect(getRecentRetreatNotices(logs, 6).map((n) => n.unitId)).toEqual(["a"]);
    expect(getRecentRetreatNotices(logs, 10).map((n) => n.unitId)).toEqual(["b"]);
  });
});
