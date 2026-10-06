/* frontend/src/utils/localSimAnalysis.ts */
import type { LocalSimManifest, LocalSimReport, LocalSimUnitStats } from "@/types/battle";

// 2つの世代の比較表と、再生位置での AI の判断を引く処理。
// 比較表の項目と書式は CLI の compare（backend/scripts/simulation/local_sim/analysis.py）に揃える。

const COMMIT_DIGITS = 7;
const HASH_DIGITS = 8;

/** 比較表の1行。差は B − A */
export interface ComparisonRow {
  label: string;
  a: string;
  b: string;
  diff: string;
}

/** 実行条件の1行 */
export interface ConditionRow {
  label: string;
  a: string;
  b: string;
  differs: boolean;
}

/** 機体ごとの比較の1行。片方の世代にいない機体は値を "-"、差を "" にする */
export interface UnitComparisonRow {
  unitId: string;
  label: string;
  isPlayer: boolean;
  kills: [string, string, string];
  deathRate: [string, string, string];
}

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const signedPt = (v: number) => `${v * 100 >= 0 ? "+" : ""}${(v * 100).toFixed(1)}pt`;
const fixed2 = (v: number) => v.toFixed(2);
const signed2 = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}`;
const perBattle = (count: number, battles: number) => (battles ? count / battles : 0);

/** 判定する機体の勝率 */
export const winRate = (r: LocalSimReport) => perBattle(r.wins, r.battles);

/** 行動の総数に占める割合 */
export function actionRatio(r: LocalSimReport, action: string): number {
  const total = Object.values(r.action_counts).reduce((sum, c) => sum + c, 0);
  return total ? (r.action_counts[action] ?? 0) / total : 0;
}

function row(
  label: string,
  a: number,
  b: number,
  fmt: (v: number) => string,
  diffFmt: (v: number) => string,
): ComparisonRow {
  return { label, a: fmt(a), b: fmt(b), diff: diffFmt(b - a) };
}

const union = (a: Record<string, number>, b: Record<string, number>) =>
  [...new Set([...Object.keys(a), ...Object.keys(b)])].sort();

/** 機体名とパイロット名 */
export function unitLabel(unit: LocalSimUnitStats): string {
  return unit.pilot_name ? `${unit.name} (${unit.pilot_name})` : unit.name;
}

/** 実行条件を並べる。違う項目は differs が true */
export function compareConditions(a: LocalSimManifest, b: LocalSimManifest): ConditionRow[] {
  const conditions = (m: LocalSimManifest): [string, string][] => [
    ["ロスター", m.roster_name],
    ["判定する機体", m.player_name ?? "-"],
    ["seed", String(m.seed)],
    ["最大ステップ数", String(m.max_steps)],
    ["コミット", `${m.git.commit?.slice(0, COMMIT_DIGITS) ?? "-"}${m.git.dirty ? " (dirty)" : ""}`],
    ["ファジィルール", m.fuzzy_rules_hash?.slice(0, HASH_DIGITS) ?? "-"],
    ["戦域", `${m.theater_id ?? "なし"} / ${m.environment} / ミノフスキー ${m.minovsky_density}`],
  ];
  const rowsB = conditions(b);
  return conditions(a).map(([label, valueA], i) => {
    const valueB = rowsB[i][1];
    return { label, a: valueA, b: valueB, differs: valueA !== valueB };
  });
}

/** 集計値を並べる。戦闘数が違っても比べられるよう、回数は1戦あたりか割合にする */
export function compareReports(a: LocalSimReport, b: LocalSimReport): ComparisonRow[] {
  return [
    row("勝率", winRate(a), winRate(b), pct, signedPt),
    row("打ち切り率", perBattle(a.timeouts, a.battles), perBattle(b.timeouts, b.battles), pct, signedPt),
    row(
      "平均戦闘時間",
      a.elapsed_time.avg,
      b.elapsed_time.avg,
      (v) => `${v.toFixed(1)}s`,
      (v) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}s`,
    ),
    row(
      "撃墜数/戦",
      perBattle(a.player_kills, a.battles),
      perBattle(b.player_kills, b.battles),
      fixed2,
      signed2,
    ),
    ...union(a.action_counts, b.action_counts).map((action) =>
      row(`行動: ${action}`, actionRatio(a, action), actionRatio(b, action), pct, signedPt),
    ),
    ...union(a.strategy_transitions, b.strategy_transitions).map((t) =>
      row(
        `遷移: ${t}`,
        perBattle(a.strategy_transitions[t] ?? 0, a.battles),
        perBattle(b.strategy_transitions[t] ?? 0, b.battles),
        (v) => `${v.toFixed(2)}/戦`,
        signed2,
      ),
    ),
  ];
}

function unitCells(
  ua: LocalSimUnitStats | undefined,
  ub: LocalSimUnitStats | undefined,
  value: (u: LocalSimUnitStats) => number,
  fmt: (v: number) => string,
  diffFmt: (v: number) => string,
): [string, string, string] {
  const va = ua ? value(ua) : null;
  const vb = ub ? value(ub) : null;
  return [
    va === null ? "-" : fmt(va),
    vb === null ? "-" : fmt(vb),
    va === null || vb === null ? "" : diffFmt(vb - va),
  ];
}

/** 機体ごとの撃墜数（1戦あたり）と被撃墜率を並べる。機体は ID で対応させる */
export function compareUnits(a: LocalSimReport, b: LocalSimReport): UnitComparisonRow[] {
  const unitsA = new Map(a.units.map((u) => [u.unit_id, u]));
  const unitsB = new Map(b.units.map((u) => [u.unit_id, u]));
  const ids = [...unitsA.keys(), ...[...unitsB.keys()].filter((id) => !unitsA.has(id))];
  return ids.map((id) => {
    const ua = unitsA.get(id);
    const ub = unitsB.get(id);
    const unit = (ua ?? ub)!;
    return {
      unitId: id,
      label: unitLabel(unit),
      isPlayer: unit.is_player,
      kills: unitCells(ua, ub, (u) => perBattle(u.kills, u.battles), fixed2, signed2),
      deathRate: unitCells(ua, ub, (u) => perBattle(u.deaths, u.battles), pct, signedPt),
    };
  });
}

/**
 * 時刻順に並んだ entries から、timestamp 以前で最後のものを返す。無ければ null。
 * 再生中は毎フレーム呼ぶため、二分探索にする。
 */
export function lastAtOrBefore<T extends { timestamp: number }>(entries: T[], timestamp: number): T | null {
  let lo = 0;
  let hi = entries.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (entries[mid].timestamp <= timestamp) lo = mid + 1;
    else hi = mid;
  }
  return lo > 0 ? entries[lo - 1] : null;
}

/** AI_DECISION のメッセージ（「… [ATTACK] を選択 …」）から、選んだ行動を取り出す */
export function chosenAction(message: string): string | null {
  return /\[([A-Z_]+)\] を選択/.exec(message)?.[1] ?? null;
}
