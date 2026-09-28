import { describe, it, expect } from "vitest";
import { formatTheaterLabel, getViewerEnvironment } from "@/utils/theater";

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
