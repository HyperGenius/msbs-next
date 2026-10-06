import { describe, expect, it } from "vitest";
import type { LocalSimManifest, LocalSimReport, LocalSimUnitStats } from "@/types/battle";
import {
  chosenAction,
  compareConditions,
  compareReports,
  compareUnits,
  lastAtOrBefore,
} from "@/utils/localSimAnalysis";

const unit = (id: string, overrides: Partial<LocalSimUnitStats> = {}): LocalSimUnitStats => ({
  unit_id: id,
  name: id,
  pilot_name: null,
  is_player: false,
  battles: 4,
  kills: 0,
  deaths: 0,
  ...overrides,
});

const report = (overrides: Partial<LocalSimReport> = {}): LocalSimReport => ({
  schema_version: 1,
  generation_id: "gen",
  battles: 4,
  wins: 2,
  losses: 2,
  timeouts: 1,
  elapsed_time: { avg: 60, min: 30, max: 90 },
  player_kills: 2,
  action_counts: { ATTACK: 1, MOVE: 3 },
  strategy_transitions: {},
  weapon_usage: {},
  units: [],
  warnings: [],
  ...overrides,
});

const manifest = (overrides: Partial<LocalSimManifest> = {}): LocalSimManifest => ({
  schema_version: 1,
  generation_id: "gen",
  label: "gen",
  created_at: "2026-10-05T00:00:00Z",
  pinned: false,
  roster_name: "roster",
  player_name: "Zaku II",
  seed: 611,
  rounds: 4,
  max_steps: 3000,
  git: { commit: "0123456789abcdef", dirty: false },
  fuzzy_rules_hash: "ae1c1073aaaaaaaa",
  theater_id: "solomon",
  environment: "SPACE",
  minovsky_density: 0.35,
  summary: { battles: 4, wins: 2, losses: 2, timeouts: 1, total_kills: 2 },
  battles: [],
  ...overrides,
});

describe("compareReports", () => {
  it("割合と1戦あたりの値を並べ、差を B − A で付ける", () => {
    const a = report();
    const b = report({
      battles: 2,
      wins: 2,
      losses: 0,
      timeouts: 0,
      elapsed_time: { avg: 45.5, min: 40, max: 51 },
      player_kills: 3,
      action_counts: { ATTACK: 1, MISS: 1 },
      strategy_transitions: { "AGGRESSIVE → DEFENSIVE": 1 },
    });

    expect(compareReports(a, b)).toEqual([
      { label: "勝率", a: "50.0%", b: "100.0%", diff: "+50.0pt" },
      { label: "打ち切り率", a: "25.0%", b: "0.0%", diff: "-25.0pt" },
      { label: "平均戦闘時間", a: "60.0s", b: "45.5s", diff: "-14.5s" },
      { label: "撃墜数/戦", a: "0.50", b: "1.50", diff: "+1.00" },
      { label: "行動: ATTACK", a: "25.0%", b: "50.0%", diff: "+25.0pt" },
      { label: "行動: MISS", a: "0.0%", b: "50.0%", diff: "+50.0pt" },
      { label: "行動: MOVE", a: "75.0%", b: "0.0%", diff: "-75.0pt" },
      { label: "遷移: AGGRESSIVE → DEFENSIVE", a: "0.00/戦", b: "0.50/戦", diff: "+0.50" },
    ]);
  });
});

describe("compareUnits", () => {
  it("機体を ID で対応させ、片方にしかいない機体は - にする", () => {
    const a = report({ units: [unit("p", { is_player: true, kills: 2, deaths: 1 }), unit("e", { deaths: 4 })] });
    const b = report({
      units: [unit("p", { is_player: true, battles: 2, kills: 2 }), unit("o", { pilot_name: "Char", battles: 2 })],
    });

    expect(compareUnits(a, b)).toEqual([
      { unitId: "p", label: "p", isPlayer: true, kills: ["0.50", "1.00", "+0.50"], deathRate: ["25.0%", "0.0%", "-25.0pt"] },
      { unitId: "e", label: "e", isPlayer: false, kills: ["0.00", "-", ""], deathRate: ["100.0%", "-", ""] },
      { unitId: "o", label: "o (Char)", isPlayer: false, kills: ["-", "0.00", ""], deathRate: ["-", "0.0%", ""] },
    ]);
  });
});

describe("compareConditions", () => {
  it("違う項目に differs を付ける", () => {
    const rows = compareConditions(manifest(), manifest({ seed: 700, git: { commit: "0123456ffff", dirty: true } }));

    expect(rows.find((r) => r.label === "seed")).toEqual({ label: "seed", a: "611", b: "700", differs: true });
    expect(rows.find((r) => r.label === "コミット")).toMatchObject({ a: "0123456", b: "0123456 (dirty)", differs: true });
    expect(rows.find((r) => r.label === "ファジィルール")).toMatchObject({ a: "ae1c1073", differs: false });
  });
});

describe("lastAtOrBefore", () => {
  const entries = [{ timestamp: 1 }, { timestamp: 2 }, { timestamp: 2 }, { timestamp: 5 }];

  it("timestamp 以前で最後のものを返す", () => {
    expect(lastAtOrBefore(entries, 2)).toBe(entries[2]);
    expect(lastAtOrBefore(entries, 4.9)).toBe(entries[2]);
    expect(lastAtOrBefore(entries, 100)).toBe(entries[3]);
  });

  it("最初のものより前か、空なら null を返す", () => {
    expect(lastAtOrBefore(entries, 0.5)).toBeNull();
    expect(lastAtOrBefore([], 1)).toBeNull();
  });
});

describe("chosenAction", () => {
  it("AI_DECISION のメッセージから選んだ行動を取り出す", () => {
    expect(chosenAction("UNKNOWN機 がファジィ推論により [HIT_AND_AWAY] を選択 (HP率:1.00)")).toBe("HIT_AND_AWAY");
    expect(chosenAction("ターゲットを選択")).toBeNull();
  });
});
