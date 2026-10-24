import { describe, it, expect } from "vitest";
import {
  buildRunArgs,
  isValidName,
  parseProgress,
  parseSavedGenerationId,
} from "@/lib/localSim/shared";
import { battleViewerUrl, compareViewerUrl } from "@/lib/localSim/viewerUrl";

describe("isValidName", () => {
  it("英数字で始まり _.- を含む名前を許可する", () => {
    expect(isValidName("solomon_test-1.0")).toBe(true);
  });
  it.each(["", "..", "-rf", ".tmp-x", "a/b", "a b", "a;b"])("%s を弾く", (name) => {
    expect(isValidName(name)).toBe(false);
  });
});

describe("buildRunArgs", () => {
  it("必須項目だけの引数を作る", () => {
    expect(buildRunArgs({ roster: "r1", rounds: 3 })).toEqual(["run", "--roster", "r1", "--rounds", "3"]);
  });
  it("任意項目を引数に足す", () => {
    expect(
      buildRunArgs({ roster: "r1", rounds: 3, seed: 0, steps: 100, label: "before", pin: true })
    ).toEqual(["run", "--roster", "r1", "--rounds", "3", "--seed", "0", "--steps", "100", "--label", "before", "--pin"]);
  });
  it.each([
    [{ roster: "../x", rounds: 1 }],
    [{ roster: "r", rounds: 0 }],
    [{ roster: "r", rounds: 1.5 }],
    [{ roster: "r", rounds: 1, seed: -1 }],
    [{ roster: "r", rounds: 1, steps: 0 }],
    [{ roster: "r", rounds: 1, label: "--pin" }],
  ])("不正なリクエストは文字列で返す %j", (request) => {
    expect(typeof buildRunArgs(request)).toBe("string");
  });
});

describe("CLI 出力の解析", () => {
  it("進捗行から完了数を取る", () => {
    expect(parseProgress("  [3/20] seed=613 WIN 撃墜 2 / 41.0s")).toBe(3);
    expect(parseProgress("保存しました: /x")).toBeNull();
  });
  it("保存先のパスから世代IDを取る", () => {
    expect(parseSavedGenerationId("保存しました: /repo/battle_logs/local_sim/generations/20261024-101010_a")).toBe(
      "20261024-101010_a"
    );
    expect(parseSavedGenerationId("  古い世代を削除しました: x")).toBeNull();
  });
});

describe("viewer URL", () => {
  it("再生と比較の URL を作る", () => {
    expect(battleViewerUrl("g1", 2, "http://h")).toBe("http://h/dev/sim?gen=g1&battle=2");
    expect(compareViewerUrl("a", "b", "http://h")).toBe("http://h/dev/sim?view=compare&a=a&b=b");
  });
});
