import { describe, it, expect } from "vitest";
import {
  formatForecastDate,
  formatTheaterLabel,
  getEnvironmentVisual,
  getMinovskyLevelLabel,
  getTerrainGradeFor,
  getViewerEnvironment,
  isUnsuitableTerrainGrade,
} from "@/utils/theater";

describe("formatTheaterLabel", () => {
  it("戦域名・環境タイプ名・濃度（%）をつなげる", () => {
    expect(
      formatTheaterLabel({
        theater_name: "ソロモン宙域",
        environment_name: "宇宙",
        minovsky_density: 0.42,
      }),
    ).toBe("ソロモン宙域（宇宙）／ミノフスキー濃度 42%");
  });

  it("濃度 0 も表示する", () => {
    expect(
      formatTheaterLabel({
        theater_name: "ソロモン宙域",
        environment_name: "宇宙",
        minovsky_density: 0,
      }),
    ).toBe("ソロモン宙域（宇宙）／ミノフスキー濃度 0%");
  });

  it("環境タイプ名・濃度が無ければ省く", () => {
    expect(
      formatTheaterLabel({
        theater_name: "ソロモン宙域",
        environment_name: null,
        minovsky_density: null,
      }),
    ).toBe("ソロモン宙域");
  });

  it("戦域の無いバトルは null", () => {
    expect(
      formatTheaterLabel({
        theater_name: null,
        environment_name: "宇宙",
        minovsky_density: 0,
      }),
    ).toBeNull();
    expect(formatTheaterLabel({})).toBeNull();
  });
});

describe("getViewerEnvironment", () => {
  it("描画プリセットを優先する", () => {
    expect(
      getViewerEnvironment({ viewer_preset: "FOREST", environment: "FOREST" }),
    ).toBe("FOREST");
  });

  it("描画プリセットが無ければ環境タイプIDを使う", () => {
    expect(
      getViewerEnvironment({ viewer_preset: null, environment: "GROUND" }),
    ).toBe("GROUND");
  });

  it("どちらも無ければ SPACE", () => {
    expect(getViewerEnvironment({})).toBe("SPACE");
  });
});

describe("getEnvironmentVisual", () => {
  it("宇宙と森林はそれぞれのアイコンにする", () => {
    expect(getEnvironmentVisual("SPACE").icon).toBe("🌌");
    expect(getEnvironmentVisual("FOREST").icon).toBe("🌲");
  });

  it("未知の環境タイプは既定のアイコンにする", () => {
    expect(getEnvironmentVisual("DESERT").icon).toBe("🛰️");
  });
});

describe("getMinovskyLevelLabel", () => {
  it("段階を低・中・高にする", () => {
    expect(getMinovskyLevelLabel("LOW")).toBe("低");
    expect(getMinovskyLevelLabel("MEDIUM")).toBe("中");
    expect(getMinovskyLevelLabel("HIGH")).toBe("高");
  });
});

describe("getTerrainGradeFor", () => {
  const forest = { environment_id: "FOREST", default_terrain_grade: "A" };

  it("機体の地形適正を返す", () => {
    expect(
      getTerrainGradeFor({ terrain_adaptability: { FOREST: "C" } }, forest),
    ).toBe("C");
  });

  it("機体に設定が無ければ環境タイプの既定ランク", () => {
    expect(
      getTerrainGradeFor({ terrain_adaptability: { SPACE: "S" } }, forest),
    ).toBe("A");
    expect(getTerrainGradeFor({}, forest)).toBe("A");
  });
});

describe("isUnsuitableTerrainGrade", () => {
  it("C 以下は不向き", () => {
    expect(isUnsuitableTerrainGrade("C")).toBe(true);
    expect(isUnsuitableTerrainGrade("D")).toBe(true);
  });

  it("B 以上は不向きではない", () => {
    expect(isUnsuitableTerrainGrade("S")).toBe(false);
    expect(isUnsuitableTerrainGrade("A")).toBe(false);
    expect(isUnsuitableTerrainGrade("B")).toBe(false);
  });
});

describe("formatForecastDate", () => {
  it("JST の月日と曜日にする", () => {
    expect(formatForecastDate("2026-10-01T12:00:00Z")).toBe("10/1(木)");
  });

  it("UTC では前日でも JST の日付にする", () => {
    expect(formatForecastDate("2026-09-30T15:00:00Z")).toBe("10/1(木)");
  });
});
