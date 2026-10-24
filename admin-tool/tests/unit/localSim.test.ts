import { describe, it, expect } from "vitest";
import {
  buildFetchArgs,
  buildRunArgs,
  isValidName,
  parseProgress,
  parseSavedGenerationId,
  parseSavedRosterName,
} from "@/lib/localSim/shared";
import { rowsToUnitSpecs, type FetchUnitRow } from "@/lib/localSim/fetchForm";
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

const MS_ID = "0f8fad5b-d9cb-469f-a165-70867728950e";

describe("buildFetchArgs", () => {
  it("機体・パイロット・NPC・戦域を引数にする", () => {
    expect(
      buildFetchArgs({
        mobile_suits: [{ id: MS_ID, team: "A" }],
        pilots: [{ id: "npc-1234", team: null }],
        npc: 4,
        ace: 1,
        theater: "solomon",
        minovsky: 0.6,
        name: "solomon_test",
        force: true,
      })
    ).toEqual([
      "fetch",
      "--ms", `${MS_ID}:A`,
      "--pilot", "npc-1234",
      "--npc", "4",
      "--ace", "1",
      "--theater", "solomon",
      "--minovsky", "0.6",
      "--name", "solomon_test",
      "--force",
    ]);
  });
  it("省略した項目は引数にしない", () => {
    expect(buildFetchArgs({ npc: 0, ace: 0, theater: "", minovsky: null, name: "" })).toEqual(["fetch"]);
  });
  it.each([
    [{ mobile_suits: [{ id: "not-a-uuid" }] }],
    [{ mobile_suits: [{ id: `--force` }] }],
    [{ pilots: [{ id: "-x" }] }],
    [{ pilots: [{ id: "user_1:A" }] }],
    [{ pilots: [{ id: "user_1", team: "a b" }] }],
    [{ npc: -1 }],
    [{ ace: 1.5 }],
    [{ npc: 101 }],
    [{ theater: "../x" }],
    [{ minovsky: 1.2 }],
    [{ name: "--force" }],
  ])("不正なリクエストは文字列で返す %j", (request) => {
    expect(typeof buildFetchArgs(request)).toBe("string");
  });
});

describe("rowsToUnitSpecs", () => {
  const row = (patch: Partial<FetchUnitRow>): FetchUnitRow => ({
    key: 1,
    kind: "player",
    pilotId: "",
    mobileSuitId: "",
    team: "",
    ...patch,
  });
  it("プレイヤーは選んだ所有機を --ms に、NPC は --pilot にする", () => {
    expect(
      rowsToUnitSpecs([
        row({ kind: "player", pilotId: "p1", mobileSuitId: MS_ID, team: " A " }),
        row({ kind: "npc", pilotId: "p2" }),
        row({ kind: "ms", mobileSuitId: ` ${MS_ID} ` }),
      ])
    ).toEqual({
      mobile_suits: [
        { id: MS_ID, team: "A" },
        { id: MS_ID, team: null },
      ],
      pilots: [{ id: "p2", team: null }],
    });
  });
  it("出撃機体を選んでいないプレイヤーは理由を返す", () => {
    expect(rowsToUnitSpecs([row({ kind: "player", pilotId: "p1" })])).toMatch(/1 行目/);
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
  it("fetch の保存先のパスからロスター名を取る", () => {
    expect(parseSavedRosterName("8 機を保存しました: /repo/battle_logs/local_sim/rosters/solomon_test.json")).toBe(
      "solomon_test"
    );
    expect(parseSavedRosterName("保存しました: /repo/battle_logs/local_sim/generations/g1")).toBeNull();
  });
});

describe("viewer URL", () => {
  it("再生と比較の URL を作る", () => {
    expect(battleViewerUrl("g1", 2, "http://h")).toBe("http://h/dev/sim?gen=g1&battle=2");
    expect(compareViewerUrl("a", "b", "http://h")).toBe("http://h/dev/sim?view=compare&a=a&b=b");
  });
});
