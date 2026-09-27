import { describe, it, expect } from "vitest";
import {
  firstErrorMessage,
  formatTechRequirement,
  newTechRequirement,
  parseThresholds,
  technologyFormSchema,
  thresholdsError,
  toTechnologyFormValues,
  toTechnologyPayload,
} from "@/lib/technology";
import { MasterTechnology } from "@/types/admin";

const BEAM: MasterTechnology = {
  id: "beam_generator_tech",
  name: "ビームジェネレータ技術",
  description: "高出力ビーム武器の開発に必要な技術",
  level_thresholds: [3, 8, 15],
  overflow_credit_value: 500,
};
const PSYCOMMU: MasterTechnology = { ...BEAM, id: "psycommu_tech", name: "サイコミュ技術" };

describe("parseThresholds", () => {
  it("カンマ・読点・空白で区切り、空の要素は無視する", () => {
    expect(parseThresholds("3, 8,15")).toEqual([3, 8, 15]);
    expect(parseThresholds("3、8 15 ")).toEqual([3, 8, 15]);
    expect(parseThresholds("")).toEqual([]);
  });
});

describe("thresholdsError", () => {
  it("正の整数の狭義単調増加なら null", () => {
    expect(thresholdsError([3, 8, 15])).toBeNull();
    expect(thresholdsError([1])).toBeNull();
  });

  it.each([
    ["空", []],
    ["0を含む", [0, 3]],
    ["同じ値を含む", [3, 3]],
    ["減少する", [8, 3]],
    ["小数を含む", [1.5, 3]],
    ["数値でない", [Number.NaN]],
  ])("%s ならエラー", (_label, thresholds) => {
    expect(thresholdsError(thresholds)).not.toBeNull();
  });
});

describe("technologyFormSchema", () => {
  const valid = toTechnologyFormValues(null);

  it("新規作成の初期値は Lv1=3 / Lv2=8 / Lv3=15", () => {
    expect(valid.level_thresholds).toBe("3, 8, 15");
    expect(technologyFormSchema.safeParse({ ...valid, id: "x_tech", name: "X" }).success).toBe(true);
  });

  it("IDはスネークケースだけを受け入れる", () => {
    expect(technologyFormSchema.safeParse({ ...valid, id: "Bad-Id", name: "X" }).success).toBe(false);
  });

  it("閾値の不正はエラー", () => {
    const result = technologyFormSchema.safeParse({ ...valid, id: "x", name: "X", level_thresholds: "8, 3" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toEqual(["level_thresholds"]);
  });

  it("フォームの値と保存リクエストを相互に変換できる", () => {
    expect(toTechnologyPayload(toTechnologyFormValues(BEAM))).toEqual(BEAM);
  });
});

describe("newTechRequirement", () => {
  it("まだ使っていない最初の技術を Lv1 で返す", () => {
    expect(newTechRequirement([BEAM, PSYCOMMU], [{ tech_id: BEAM.id, required_lv: 2 }])).toEqual({
      tech_id: PSYCOMMU.id,
      required_lv: 1,
    });
  });

  it("全て使用済みなら null", () => {
    expect(newTechRequirement([BEAM], [{ tech_id: BEAM.id, required_lv: 1 }])).toBeNull();
  });
});

describe("formatTechRequirement", () => {
  it("技術名とLvで表示し、マスターに無ければIDで表示する", () => {
    expect(formatTechRequirement({ tech_id: PSYCOMMU.id, required_lv: 2 }, [BEAM, PSYCOMMU])).toBe(
      "サイコミュ技術 Lv2"
    );
    expect(formatTechRequirement({ tech_id: "gone", required_lv: 1 }, [BEAM])).toBe("gone Lv1");
  });
});

describe("firstErrorMessage", () => {
  it("ネストしたエラーから最初の文言を返す", () => {
    expect(firstErrorMessage([undefined, { tech_id: { message: "同じ技術が2つある" } }])).toBe(
      "同じ技術が2つある"
    );
    expect(firstErrorMessage(undefined)).toBeUndefined();
  });
});
