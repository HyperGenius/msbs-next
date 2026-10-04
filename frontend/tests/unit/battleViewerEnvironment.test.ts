/* frontend/tests/unit/battleViewerEnvironment.test.ts */
import { describe, it, expect } from "vitest";
import {
  getEnvironmentColor,
  getMinovskyHazeOpacity,
  toSupportedEnvironment,
} from "@/components/BattleViewer/utils";
import {
  getTreeCount,
  layoutGrove,
  MAX_TREES_PER_GROVE,
  MIN_TREES_PER_GROVE,
} from "@/components/BattleViewer/utils/forestLayout";
import { Obstacle } from "@/types/battle";

const SCALE = 0.05;

function makeObstacle(overrides: Partial<Obstacle> = {}): Obstacle {
  return {
    obstacle_id: "auto_obs_0",
    position: { x: 2000, y: 0, z: 3000 },
    radius: 120,
    height: 180,
    ...overrides,
  };
}

describe("toSupportedEnvironment", () => {
  it("FOREST は森林の描画を使う", () => {
    expect(toSupportedEnvironment("FOREST")).toBe("FOREST");
  });

  it("未知の描画プリセットは SPACE にフォールバックする", () => {
    expect(toSupportedEnvironment("VOLCANO")).toBe("SPACE");
    expect(toSupportedEnvironment("")).toBe("SPACE");
  });

  it("FOREST の背景色は SPACE と異なる", () => {
    expect(getEnvironmentColor("FOREST")).not.toBe(getEnvironmentColor("SPACE"));
  });
});

describe("getMinovskyHazeOpacity", () => {
  it("濃度 0・未設定ではもやを出さない", () => {
    expect(getMinovskyHazeOpacity(0)).toBe(0);
    expect(getMinovskyHazeOpacity(null)).toBe(0);
    expect(getMinovskyHazeOpacity(undefined)).toBe(0);
    expect(getMinovskyHazeOpacity(-0.2)).toBe(0);
    expect(getMinovskyHazeOpacity(Number.NaN)).toBe(0);
  });

  it("濃度が高いほど濃くなる", () => {
    const low = getMinovskyHazeOpacity(0.2);
    const high = getMinovskyHazeOpacity(0.9);
    expect(low).toBeGreaterThan(0);
    expect(high).toBeGreaterThan(low);
  });

  it("濃度 1 を超えても不透明度は濃度 1 と同じ", () => {
    expect(getMinovskyHazeOpacity(1.5)).toBe(getMinovskyHazeOpacity(1));
    expect(getMinovskyHazeOpacity(1)).toBeLessThanOrEqual(1);
  });
});

describe("getTreeCount", () => {
  it("小さい木立でも最低本数を並べる", () => {
    expect(getTreeCount(0.5)).toBe(MIN_TREES_PER_GROVE);
  });

  it("大きい木立でも上限本数を超えない", () => {
    expect(getTreeCount(100)).toBe(MAX_TREES_PER_GROVE);
  });
});

describe("layoutGrove", () => {
  it("木はすべて障害物の半径の範囲に収まる", () => {
    const obstacle = makeObstacle();
    const cx = obstacle.position.x * SCALE;
    const cz = obstacle.position.z * SCALE;
    const radius = obstacle.radius * SCALE;
    const trees = layoutGrove(obstacle, SCALE);

    expect(trees.length).toBe(getTreeCount(radius));
    for (const tree of trees) {
      expect(Math.hypot(tree.x - cx, tree.z - cz)).toBeLessThanOrEqual(radius);
      expect(tree.obstacleId).toBe(obstacle.obstacle_id);
      expect(tree.height).toBeGreaterThan(0);
      expect(tree.canopyRadius).toBeGreaterThan(0);
    }
  });

  it("同じ障害物 ID なら毎回同じ配置になる", () => {
    const obstacle = makeObstacle();
    expect(layoutGrove(obstacle, SCALE)).toEqual(layoutGrove(obstacle, SCALE));
  });

  it("障害物 ID が違えば配置も変わる", () => {
    const a = layoutGrove(makeObstacle({ obstacle_id: "auto_obs_0" }), SCALE);
    const b = layoutGrove(makeObstacle({ obstacle_id: "auto_obs_1" }), SCALE);
    expect(a).not.toEqual(b);
  });
});
