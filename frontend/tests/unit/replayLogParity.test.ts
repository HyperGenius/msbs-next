/* frontend/tests/unit/replayLogParity.test.ts */
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import { describe, it, expect } from "vitest";
import {
  getBattleSnapshot,
  getDetectedUnits,
  isEnShortageLog,
  SnapshotCache,
  UnitSnapshot,
} from "@/components/BattleViewer/hooks/useBattleSnapshot";
import { computeBattleChapters } from "@/components/BattleViewer/hooks/useBattleChapters";
import {
  computeAttackEvents,
  computeAttackingUnitIds,
  hasDisengageLog,
} from "@/components/BattleViewer/hooks/useBattleEvents";
import { extractHudAttackLogs, selectHudLogLines } from "@/components/BattleViewer/hooks/useHudAttackLog";
import { SIMULATION_STEP_S } from "@/components/BattleViewer/utils";
import {
  BattleLog,
  MobileSuit,
  REPLAY_LOG_VERSION,
  ReplayBattleLog,
  ReplayLogHeader,
} from "@/types/battle";

// バックエンドの replay-fixture で作る。tests/unit/test_replay_log.py も同じファイルを読む。
const FIXTURE_PATH = fileURLToPath(
  new URL("../../../backend/tests/fixtures/replay_log_parity.json.gz", import.meta.url)
);

interface ReplayFixture {
  player_info: MobileSuit;
  enemies_info: MobileSuit[];
  stored_logs: BattleLog[];
  replay_logs: [ReplayLogHeader, ...ReplayBattleLog[]];
}

const fixture: ReplayFixture = JSON.parse(gunzipSync(readFileSync(FIXTURE_PATH)).toString("utf-8"));
const [header, ...replayEntries] = fixture.replay_logs;
const stored = fixture.stored_logs;
// ビューアの部品は BattleLog を受け取る。配信用ログで省いた message は、これらの部品が読まない行のものだけ
const replay = replayEntries as unknown as BattleLog[];
const units = [fixture.player_info, ...fixture.enemies_info];

// 座標・速度の丸め（0.1m・0.1m/s）と、外挿の上限 1 秒から決めた誤差の上限
const POSITION_TOLERANCE_M = 0.15;
// 向きの丸め（0.1 度）の誤差の上限
const HEADING_TOLERANCE_DEG = 0.1;

/** 再生時刻の一覧。TurnController と同じく 0.1 秒刻みで丸める */
function replayTimestamps(logs: BattleLog[]): number[] {
  const max = logs[logs.length - 1].timestamp;
  const steps = Math.round(max / SIMULATION_STEP_S);
  return Array.from({ length: steps + 1 }, (_, i) => Math.round(i * SIMULATION_STEP_S * 10) / 10);
}

/** 時刻を配信用ログと同じく小数2桁に丸める */
function roundTimestamp(timestamp: number): number {
  return Math.round(timestamp * 100) / 100;
}

/** 角度の差を -180〜180 度に直す */
function angleDiff(a: number, b: number): number {
  return ((((a - b + 180) % 360) + 360) % 360) - 180;
}

/** 位置と向き以外が一致し、位置と向きが丸めの誤差に収まることを確かめる */
function expectSameSnapshot(a: UnitSnapshot, b: UnitSnapshot, context: string): void {
  expect({ hp: b.hp, ammo: b.ammo, warnings: b.warnings, targetId: b.targetId }, context).toEqual({
    hp: a.hp,
    ammo: a.ammo,
    warnings: a.warnings,
    targetId: a.targetId,
  });
  expect(b.en, context).toBeCloseTo(a.en, 6);
  for (const axis of ["x", "y", "z"] as const) {
    expect(Math.abs(b.pos[axis] - a.pos[axis]), `${context} pos.${axis}`).toBeLessThanOrEqual(POSITION_TOLERANCE_M);
  }
  expect(b.heading === undefined, context).toBe(a.heading === undefined);
  if (a.heading !== undefined && b.heading !== undefined) {
    expect(Math.abs(angleDiff(b.heading, a.heading)), `${context} heading`).toBeLessThanOrEqual(HEADING_TOLERANCE_DEG);
  }
}

/** 1 時刻分のログを BattleViewer と同じ条件で選ぶ */
function logsAt(logs: BattleLog[], timestamp: number): BattleLog[] {
  return logs.filter((log) => Math.abs(log.timestamp - timestamp) < 1e-9);
}

/** 自機以外の機体の一覧 */
function othersOf(unit: MobileSuit): MobileSuit[] {
  return units.filter((u) => u.id !== unit.id);
}

describe("配信用ログのフィクスチャ", () => {
  it("先頭行がヘッダーで、比べる意味のある戦闘になっている", () => {
    expect(header).toEqual({ replay_version: REPLAY_LOG_VERSION });
    expect(replayEntries.every((log) => !("replay_version" in log))).toBe(true);
    expect(replay.length).toBeLessThan(stored.length);
    // 撃破・クリティカル・EN の記録・相手の切り替えを含む
    expect(stored.some((log) => log.action_type === "DESTROYED")).toBe(true);
    expect(stored.some((log) => log.is_crit)).toBe(true);
    expect(stored.some((log) => typeof log.details?.en === "number")).toBe(true);
    const targetChanges = new Set(
      replay.filter((log) => log.action_type === "TARGET_SELECTION").map((log) => `${log.actor_id}:${log.target_id}`)
    );
    expect(targetChanges.size).toBeGreaterThan(units.length);
  });
});

describe("旧形式と配信用ログでビューアの表示状態が一致する", () => {
  const timestamps = replayTimestamps(stored);

  it("再生の長さが同じ", () => {
    expect(replay[replay.length - 1].timestamp).toBeCloseTo(stored[stored.length - 1].timestamp, 9);
  });

  it("各機体の位置・HP・EN・弾数・警告・向き・ターゲットが一致する", () => {
    // BattleViewer と同じく、現在の時刻と 1 ステップ前の時刻をキャッシュ付きで順に求める
    const storedCache: SnapshotCache = new Map();
    const replayCache: SnapshotCache = new Map();
    for (const t of timestamps) {
      for (const unit of units) {
        for (const [ts, key] of [
          [t, unit.id],
          [t - SIMULATION_STEP_S, `${unit.id}:prev`],
        ] as const) {
          const a = getBattleSnapshot(unit.id, unit, stored, ts, storedCache, key);
          const b = getBattleSnapshot(unit.id, unit, replay, ts, replayCache, key);
          expectSameSnapshot(a, b, `${unit.name} (${unit.id}) @ ${ts}`);
        }
      }
    }
  });

  it("索敵済みの機体が一致する", () => {
    for (const t of timestamps) {
      for (const unit of units) {
        expect(getDetectedUnits(unit.id, replay, t), `${unit.id} @ ${t}`).toEqual(getDetectedUnits(unit.id, stored, t));
      }
    }
  });

  it("攻撃の演出・攻撃中の機体・仕切り直しが一致する", () => {
    const beamWeaponIds = new Set(
      units.flatMap((u) => (u.weapons ?? []).filter((w) => w.type === "BEAM").map((w) => w.id))
    );
    let attackCount = 0;
    for (const t of timestamps) {
      const a = logsAt(stored, t);
      const b = logsAt(replay, t);
      const attacks = computeAttackEvents(a, beamWeaponIds);
      attackCount += attacks.length;
      expect(computeAttackEvents(b, beamWeaponIds), `@ ${t}`).toEqual(attacks);
      expect(computeAttackingUnitIds(b), `@ ${t}`).toEqual(computeAttackingUnitIds(a));
      for (const unit of units) {
        expect(hasDisengageLog(b, unit.id), `${unit.id} @ ${t}`).toBe(hasDisengageLog(a, unit.id));
      }
    }
    expect(attackCount).toBeGreaterThan(0);
  });

  it("チャプターが一致する", () => {
    // id はログの位置から作るため、行を省いた配信用ログでは値が変わる。時刻は配信用ログと同じ桁に丸めて比べる
    const withoutId = (logs: BattleLog[], unit: MobileSuit) =>
      computeBattleChapters(logs, unit, othersOf(unit)).map(({ timestamp, kind, icon, label, detail, accentColor }) => ({
        timestamp: roundTimestamp(timestamp),
        kind,
        icon,
        label,
        detail,
        accentColor,
      }));
    let chapterCount = 0;
    for (const unit of units) {
      const chapters = withoutId(stored, unit);
      chapterCount += chapters.length;
      expect(withoutId(replay, unit), unit.id).toEqual(chapters);
    }
    expect(chapterCount).toBeGreaterThan(0);
  });

  it("HUD ログの行と EN 不足の時刻が一致する", () => {
    const names = new Map(units.map((u) => [u.id, u.name]));
    const storedAttacks = extractHudAttackLogs(stored);
    const replayAttacks = extractHudAttackLogs(replay);
    expect(replayAttacks.length).toBe(storedAttacks.length);
    for (const unit of units) {
      for (const t of timestamps) {
        const params = { currentTimestamp: t, names, playerId: unit.id, limit: 5, maxAgeSeconds: 3 };
        expect(selectHudLogLines({ ...params, attackLogs: replayAttacks }), `${unit.id} @ ${t}`).toEqual(
          selectHudLogLines({ ...params, attackLogs: storedAttacks })
        );
      }
      const enShortage = (logs: BattleLog[]) =>
        logs.filter((log) => log.actor_id === unit.id && isEnShortageLog(log)).map((log) => log.timestamp);
      expect(enShortage(replay)).toEqual(enShortage(stored).map(roundTimestamp));
    }
  });
});
