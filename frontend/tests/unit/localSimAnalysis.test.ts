import { describe, expect, it } from "vitest";
import type {
  LocalSimBattle,
  LocalSimManifest,
  LocalSimObjectiveStats,
  LocalSimReport,
  LocalSimUnitStats,
} from "@/types/battle";
import { localSimBattleToResult } from "@/services/localSim";
import { getObjectiveSummary } from "@/utils/missionName";
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
  schema_version: 2,
  generation_id: "gen",
  battles: 4,
  wins: 2,
  losses: 2,
  draws: 0,
  timeouts: 1,
  elapsed_time: { avg: 60, min: 30, max: 90 },
  player_kills: 2,
  action_counts: { ATTACK: 1, MOVE: 3 },
  strategy_transitions: {},
  weapon_usage: {},
  units: [],
  objective: null,
  warnings: [],
  ...overrides,
});

const objective = (overrides: Partial<LocalSimObjectiveStats> = {}): LocalSimObjectiveStats => ({
  mission_name: "撤退支援",
  battles: 4,
  success: 2,
  failure: 1,
  draw: 1,
  required: 2,
  total: 3,
  progress: 6,
  lost: 3,
  progress_counts: { "0": 1, "1": 1, "2": 1, "3": 1 },
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

describe("compareReports（作戦）", () => {
  it("どちらかに作戦があれば、作戦の成功率と離脱・撃破された友軍の数を並べる", () => {
    const a = report({ objective: objective() });
    const b = report({ objective: objective({ battles: 2, success: 2, failure: 0, draw: 0, progress: 6, lost: 0 }) });

    expect(compareReports(a, b).slice(2, 5)).toEqual([
      { label: "作戦成功率", a: "50.0%", b: "100.0%", diff: "+50.0pt" },
      { label: "離脱した友軍/戦", a: "1.50", b: "3.00", diff: "+1.50" },
      { label: "撃破された友軍/戦", a: "0.75", b: "0.00", diff: "-0.75" },
    ]);
  });

  it("作戦の無い世代どうしでは作戦の行を出さない", () => {
    expect(compareReports(report(), report()).map((r) => r.label)).not.toContain("作戦成功率");
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

  it("作戦の名前を並べ、作戦の無い世代は「なし」にする", () => {
    const rows = compareConditions(manifest(), manifest({ mission_name: "撤退支援" }));

    expect(rows.find((r) => r.label === "作戦")).toEqual({ label: "作戦", a: "なし", b: "撤退支援", differs: true });
  });
});

const battle = (overrides: Partial<LocalSimBattle> = {}): LocalSimBattle => ({
  index: 1,
  seed: 611,
  win_loss: "WIN",
  kills: 1,
  elapsed_time: 30,
  steps_used: 300,
  timed_out: false,
  environment: "SPACE",
  theater_id: null,
  theater_name: null,
  environment_name: null,
  viewer_preset: null,
  minovsky_density: 0,
  player_info: { id: "p" } as LocalSimBattle["player_info"],
  enemies_info: [],
  obstacles_info: [],
  map_bounds: [0, 2000],
  log_count: 10,
  ...overrides,
});

describe("localSimBattleToResult", () => {
  it("作戦の戦闘は、作戦の結果と撤退ポイント・ロールを BattleResult に移す", () => {
    const detail = {
      total: 3,
      lost: 1,
      retreat_points: [{ position: { x: -900, y: 0, z: 0 }, radius: 120, team_id: "t" }],
      unit_roles: { a1: "WITHDRAW" },
    };
    const result = localSimBattleToResult(
      manifest(),
      battle({
        win_loss: "DRAW",
        mission_id: 4,
        mission_name: "撤退支援",
        objective_status: "DRAW",
        objective_progress: 1,
        objective_required: 2,
        objective_detail: detail,
      }),
    );

    expect(result.win_loss).toBe("DRAW");
    expect(result.mission_id).toBe(4);
    expect(result.objective_detail).toEqual(detail);
    expect(getObjectiveSummary(result)).toEqual({ status: "DRAW", progress: 1, required: 2, total: 3, lost: 1 });
  });

  it("作戦の無い戦闘と古い世代は、作戦の結果を持たない", () => {
    const result = localSimBattleToResult(manifest(), battle());

    expect(result.mission_id).toBeNull();
    expect(result.objective_detail).toBeNull();
    expect(getObjectiveSummary(result)).toBeNull();
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
