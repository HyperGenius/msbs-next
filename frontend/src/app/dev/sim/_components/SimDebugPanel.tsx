/* frontend/src/app/dev/sim/_components/SimDebugPanel.tsx */
"use client";

import { useMemo, useState } from "react";
import { LocalSimDecisionLog, MobileSuit } from "@/types/battle";
import { useLocalSimDecisionLogs } from "@/services/api";
import { chosenAction, lastAtOrBefore } from "@/utils/localSimAnalysis";

interface SimDebugPanelProps {
  generationId: string;
  index: number;
  /** 判定する機体を先頭にした全ユニット */
  units: MobileSuit[];
  currentTimestamp: number;
}

type NumberRecord = Record<string, number>;

// 同じ名前の候補を見分けるために付ける機体 ID の桁数。
const ID_DIGITS = 4;

function isNumberRecord(value: unknown): value is NumberRecord {
  return (
    typeof value === "object" && value !== null && Object.values(value).every((v) => typeof v === "number")
  );
}

/** 選んだ機体の、再生位置で有効な AI の判断（strategy_mode と fuzzy_scores）を表示する。 */
export default function SimDebugPanel({ generationId, index, units, currentTimestamp }: SimDebugPanelProps) {
  const [unitId, setUnitId] = useState<string | null>(units[0]?.id ?? null);
  const { decisions, isLoading, isError } = useLocalSimDecisionLogs(generationId, index, unitId);

  // AI_DECISION と TARGET_SELECTION は記録される間隔が違うため、それぞれ直近の1件を引く。
  const { aiDecisions, targetSelections } = useMemo(
    () => ({
      aiDecisions: (decisions ?? []).filter((d) => d.action_type === "AI_DECISION"),
      targetSelections: (decisions ?? []).filter(
        (d) => d.action_type === "TARGET_SELECTION" && d.fuzzy_scores,
      ),
    }),
    [decisions],
  );
  const names = useMemo(() => new Map(units.map((u) => [u.id, u.name])), [units]);
  const aiDecision = lastAtOrBefore(aiDecisions, currentTimestamp);
  const targetSelection = lastAtOrBefore(targetSelections, currentTimestamp);

  return (
    <section className="mt-3 rounded border border-gray-700 bg-gray-900/60 p-3 text-xs text-gray-300">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <h3 className="font-bold text-gray-400">AI の判断（デバッグ）</h3>
        <select
          value={unitId ?? ""}
          onChange={(e) => setUnitId(e.target.value)}
          className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-green-300"
          aria-label="判断を表示する機体"
        >
          {units.map((u, i) => (
            <option key={u.id} value={u.id}>
              {i === 0 ? "★ " : ""}
              {u.name}
              {u.pilot_name ? ` (${u.pilot_name})` : ""}
            </option>
          ))}
        </select>
      </div>

      {isError ? (
        <p className="text-red-400" role="alert">
          判断ログを読み込めませんでした: {String(isError.message ?? isError)}
        </p>
      ) : isLoading || !decisions ? (
        <p className="text-gray-500">判断ログを読み込み中...</p>
      ) : decisions.length === 0 ? (
        <p className="text-gray-500">この機体には fuzzy_scores・strategy_mode のログがありません。</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          <AiDecisionView decision={aiDecision} />
          <TargetSelectionView decision={targetSelection} names={names} />
        </div>
      )}
    </section>
  );
}

/** 行動の判断（AI_DECISION）。fuzzy_scores は出力変数ごとの集合の活性化度 */
function AiDecisionView({ decision }: { decision: LocalSimDecisionLog | null }) {
  if (!decision) return <p className="text-gray-500">この時点までに行動の判断はありません。</p>;
  const chosen = chosenAction(decision.message);
  const outputs = Object.entries(decision.fuzzy_scores ?? {}).filter(
    (entry): entry is [string, NumberRecord] => isNumberRecord(entry[1]),
  );
  return (
    <div>
      <p className="mb-1">
        <span className="text-gray-500">行動の判断</span> t=
        {decision.timestamp.toFixed(1)}s · <span className="text-gray-500">戦略</span>{" "}
        <span className="font-bold text-green-300">{decision.strategy_mode ?? "-"}</span>
        {chosen && (
          <>
            {" "}
            · <span className="text-gray-500">選択</span>{" "}
            <span className="font-bold text-green-300">{chosen}</span>
          </>
        )}
      </p>
      {outputs.map(([variable, sets]) => (
        <ScoreBars key={variable} title={variable} scores={sets} highlight={chosen} />
      ))}
      <p className="mt-1 text-[10px] text-gray-500 break-all">{decision.message}</p>
    </div>
  );
}

/** ターゲットの選択（TARGET_SELECTION）。候補ごとの優先度スコアと、選んだ候補の入力値 */
function TargetSelectionView({
  decision,
  names,
}: {
  decision: LocalSimDecisionLog | null;
  names: Map<string, string>;
}) {
  if (!decision?.fuzzy_scores) {
    return <p className="text-gray-500">この時点までにファジィ推論でのターゲット選択はありません。</p>;
  }
  const scores = decision.fuzzy_scores;
  const allScores = isNumberRecord(scores.all_scores) ? scores.all_scores : {};
  const inputs = isNumberRecord(scores.inputs) ? scores.inputs : {};
  const selectedId = typeof scores.selected_target_id === "string" ? scores.selected_target_id : null;
  // 同じ機体名の NPC が複数いることがあるため、候補は機体 ID で持ち、名前は表示にだけ使う。
  const nameCounts = new Map<string, number>();
  for (const id of Object.keys(allScores)) {
    const name = names.get(id) ?? id;
    nameCounts.set(name, (nameCounts.get(name) ?? 0) + 1);
  }
  const candidateLabel = (id: string) => {
    const name = names.get(id);
    if (!name) return id.slice(0, ID_DIGITS);
    return (nameCounts.get(name) ?? 0) > 1 ? `${name} #${id.slice(0, ID_DIGITS)}` : name;
  };
  return (
    <div>
      <p className="mb-1">
        <span className="text-gray-500">ターゲット選択</span> t=
        {decision.timestamp.toFixed(1)}s
      </p>
      <ScoreBars title="target_priority" scores={allScores} highlight={selectedId} label={candidateLabel} />
      <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 text-[10px] text-gray-400">
        {Object.entries(inputs).map(([name, value]) => (
          <div key={name} className="contents">
            <dt className="text-gray-500">{name}</dt>
            <dd>{Number.isInteger(value) ? value : value.toFixed(3)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

/** 0〜1 のスコアを、高い順に横棒で並べる。scores と highlight のキーは一意な値（集合名・機体 ID） */
function ScoreBars({
  title,
  scores,
  highlight,
  label = (key) => key,
}: {
  title: string;
  scores: NumberRecord;
  highlight: string | null;
  label?: (key: string) => string;
}) {
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  return (
    <div className="mb-1">
      <p className="text-[10px] text-gray-500">{title}</p>
      <ul>
        {sorted.map(([key, score]) => {
          const selected = key === highlight;
          return (
            <li key={key} className="grid grid-cols-[7.5rem_1fr_2.5rem] items-center gap-2">
              <span className={`truncate ${selected ? "font-bold text-green-300" : "text-gray-400"}`}>
                {label(key)}
              </span>
              <span className="h-2 rounded bg-gray-800">
                <span
                  className={`block h-2 rounded ${selected ? "bg-green-400" : "bg-green-800"}`}
                  style={{ width: `${Math.min(Math.max(score, 0), 1) * 100}%` }}
                />
              </span>
              <span className="text-right tabular-nums">{score.toFixed(2)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
