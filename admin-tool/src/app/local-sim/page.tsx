"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  useLocalSimGeneration,
  useLocalSimGenerations,
  useLocalSimRosters,
  useLocalSimRun,
} from "@/hooks/useLocalSim";
import { battleViewerUrl, compareViewerUrl } from "@/lib/localSim/viewerUrl";
import type { LocalSimManifest, LocalSimRun } from "@/types/localSim";
import { SciFiButton, SciFiHeading, SciFiPanel } from "@/components/ui";
import LocalSimRosterForm from "@/components/admin/LocalSimRosterForm";

const MAX_COMPARE = 2;
const inputClass = "w-full bg-black/60 border border-[#00ff41]/40 px-2 py-1 text-sm text-[#00ff41]";

function percent(numerator: number, denominator: number): string {
  return denominator > 0 ? `${((numerator / denominator) * 100).toFixed(1)}%` : "-";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ja-JP");
}

const STATUS_LABELS: Record<LocalSimRun["status"], string> = {
  running: "実行中",
  succeeded: "完了",
  failed: "失敗",
  cancelled: "中止しました",
};

/** 実行中・直近のジョブの状態。失敗したときは CLI の標準エラーを出す。 */
function RunStatus({ run, summary, onCancel }: { run: LocalSimRun; summary: string; onCancel: () => void }) {
  const isRunning = run.status === "running";
  const total = run.kind === "run" ? run.request.rounds : 0;
  return (
    <div className="space-y-2 text-xs">
      <div className="flex items-center gap-3">
        <p>
          {summary} — {STATUS_LABELS[run.status]}
        </p>
        {isRunning && (
          <SciFiButton size="sm" variant="danger" onClick={onCancel}>
            中止
          </SciFiButton>
        )}
      </div>
      {isRunning && run.kind === "run" && (
        <div className="h-2 bg-black/60 border border-[#00ff41]/40">
          <div className="h-full bg-[#00ff41]" style={{ width: `${(run.completed / Math.max(total, 1)) * 100}%` }} />
        </div>
      )}
      {run.status === "failed" && run.error && (
        <pre className="whitespace-pre-wrap text-red-400 max-h-48 overflow-auto">{run.error}</pre>
      )}
      <pre className="whitespace-pre-wrap text-[#00ff41]/60 max-h-48 overflow-auto">
        {run.lines.slice(run.kind === "fetch" ? -20 : -8).join("\n")}
      </pre>
    </div>
  );
}

export default function LocalSimPage() {
  const { root, rosters, error: rostersError, refresh: refreshRosters } = useLocalSimRosters();
  const { generations, error: generationsError, refresh, setPinned } = useLocalSimGenerations();
  const { run, isRunning, start, startFetch, cancel } = useLocalSimRun();

  // 手で選んだロスター。世代と同じく、その後に作ったロスターを優先して選ぶ。
  const [rosterPick, setRosterPick] = useState<{ name: string; runKey: string | null } | null>(null);
  const [rounds, setRounds] = useState("20");
  const [seed, setSeed] = useState("");
  const [steps, setSteps] = useState("");
  const [label, setLabel] = useState("");
  const [pin, setPin] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  // 手で選んだ世代。選んだ時点の実行（started_at）を覚え、その後に終わった実行の世代を優先して開く。
  const [picked, setPicked] = useState<{ id: string; runKey: string | null } | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);

  // 実行が終わったら世代（fetch ならロスター）の一覧を取り直す。
  const handledRunRef = useRef<string | null>(null);
  useEffect(() => {
    if (!run || run.status === "running" || handledRunRef.current === run.started_at) return;
    handledRunRef.current = run.started_at;
    void (run.kind === "fetch" ? refreshRosters() : refresh());
  }, [run, refresh, refreshRosters]);

  const runKey = run?.started_at ?? null;
  const finishedGenerationId = run?.kind === "run" && run.status !== "running" ? run.generation_id : null;
  const selectedId =
    picked && picked.runKey === runKey
      ? picked.id
      : (finishedGenerationId ?? picked?.id ?? null);
  const { detail } = useLocalSimGeneration(selectedId);

  const createdRoster = run?.kind === "fetch" && run.status === "succeeded" ? run.roster_name : null;
  const selectedRoster =
    (rosterPick && rosterPick.runKey === runKey ? rosterPick.name : null) ??
    createdRoster ??
    rosterPick?.name ??
    rosters[0]?.name ??
    "";

  async function handleStart() {
    setMessage(null);
    const optionalInt = (value: string) => (value.trim() === "" ? null : Number(value));
    try {
      await start({
        roster: selectedRoster,
        rounds: Number(rounds),
        seed: optionalInt(seed),
        steps: optionalInt(steps),
        label: label.trim() || null,
        pin,
      });
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "実行を開始できません。");
    }
  }

  async function handleCancel() {
    setMessage(null);
    try {
      await cancel();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "中止できません。");
    }
  }

  async function handlePin(generation: LocalSimManifest) {
    setMessage(null);
    try {
      await setPinned(generation.generation_id, !generation.pinned);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "ピン留めを変更できません。");
    }
  }

  function toggleCompare(generationId: string) {
    setCompareIds((ids) =>
      ids.includes(generationId)
        ? ids.filter((id) => id !== generationId)
        : [...ids, generationId].slice(-MAX_COMPARE)
    );
  }

  const report = detail?.report;
  const manifest = detail?.manifest;

  return (
    <main className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <SciFiHeading level={1}>ローカルシミュレータ</SciFiHeading>
        <Link href="/" className="text-sm text-[#00ff41]/70 hover:underline">
          ← トップ
        </Link>
      </div>
      <p className="text-xs text-[#00ff41]/60">
        読み込み元: {root ?? "-"}（backend のサーバー・DB・GCS は使いません）。再生は frontend の /dev/sim を別タブで開きます。
      </p>
      {(rostersError || generationsError) && (
        <p className="text-sm text-red-400">
          読み込みに失敗しました。`next dev` で起動しているか確認してください。
        </p>
      )}
      {message && <p className="text-sm text-red-400">{message}</p>}

      <SciFiPanel className="p-4 space-y-3">
        <SciFiHeading level={2}>ロスター作成（fetch）</SciFiHeading>
        <p className="text-xs text-[#00ff41]/60">
          本番DBへは `NEON_READONLY_DATABASE_URL`（Read Only のロール）で読むだけです。プレイヤーの出撃機体はエントリーごとに決まるため、所有機から毎回選びます。
          選択肢は管理API（backend の接続先DB）から引きます。
        </p>
        <LocalSimRosterForm rosterNames={rosters.map((r) => r.name)} disabled={isRunning} onSubmit={startFetch} />
        {run?.kind === "fetch" && (
          <RunStatus
            run={run}
            summary={
              run.roster_name
                ? `ロスター ${run.roster_name}`
                : `ロスター ${run.request.name || "（日時から作る）"}`
            }
            onCancel={handleCancel}
          />
        )}
      </SciFiPanel>

      <SciFiPanel className="p-4 space-y-3">
        <SciFiHeading level={2}>実行</SciFiHeading>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <label className="space-y-1">
            <span>ロスター</span>
            <select
              className={inputClass}
              value={selectedRoster}
              onChange={(e) => setRosterPick({ name: e.target.value, runKey })}
              disabled={isRunning}
            >
              {rosters.length === 0 && <option value="">（ロスターがありません）</option>}
              {rosters.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.name}（{r.entries}機{r.theater_id ? ` / ${r.theater_id}` : ""}）
                </option>
              ))}
            </select>
            {selectedRoster && (
              <Link href={`/local-sim/rosters/${encodeURIComponent(selectedRoster)}`} className="text-xs text-[#00ff41]/70 hover:underline">
                このロスターを編集
              </Link>
            )}
          </label>
          <label className="space-y-1">
            <span>戦闘数</span>
            <input className={inputClass} type="number" min={1} value={rounds} onChange={(e) => setRounds(e.target.value)} disabled={isRunning} />
          </label>
          <label className="space-y-1">
            <span>シード（省略可）</span>
            <input className={inputClass} type="number" min={0} value={seed} onChange={(e) => setSeed(e.target.value)} disabled={isRunning} />
          </label>
          <label className="space-y-1">
            <span>最大ステップ数（省略可）</span>
            <input className={inputClass} type="number" min={1} value={steps} onChange={(e) => setSteps(e.target.value)} disabled={isRunning} />
          </label>
          <label className="space-y-1">
            <span>ラベル（省略可）</span>
            <input className={inputClass} value={label} onChange={(e) => setLabel(e.target.value)} disabled={isRunning} />
          </label>
          <label className="flex items-end gap-2 pb-1">
            <input type="checkbox" checked={pin} onChange={(e) => setPin(e.target.checked)} disabled={isRunning} />
            <span>ピン留めする</span>
          </label>
        </div>
        <SciFiButton onClick={handleStart} disabled={isRunning || !selectedRoster}>
          {isRunning ? "実行中…" : "実行"}
        </SciFiButton>
        {run?.kind === "run" && (
          <RunStatus
            run={run}
            summary={`${run.request.roster}: ${run.completed}/${run.request.rounds} 戦`}
            onCancel={handleCancel}
          />
        )}
      </SciFiPanel>

      <SciFiPanel className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <SciFiHeading level={2}>世代（新しい順）</SciFiHeading>
          <SciFiButton
            size="sm"
            variant="accent"
            disabled={compareIds.length !== MAX_COMPARE}
            onClick={() => window.open(compareViewerUrl(compareIds[0], compareIds[1]), "_blank", "noopener")}
          >
            選んだ2世代を比較
          </SciFiButton>
        </div>
        {generations.length === 0 ? (
          <p className="text-sm text-[#00ff41]/60">世代がありません。</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-[#00ff41]/60">
                <th>比較</th><th>ラベル</th><th>作戦</th><th>日時</th><th>戦闘数</th><th>勝敗</th><th>打ち切り</th><th>ピン</th><th />
              </tr>
            </thead>
            <tbody>
              {generations.map((g) => (
                <tr key={g.generation_id} className={g.generation_id === selectedId ? "bg-[#00ff41]/10" : ""}>
                  <td><input type="checkbox" checked={compareIds.includes(g.generation_id)} onChange={() => toggleCompare(g.generation_id)} /></td>
                  <td>{g.label}{g.source === "production" ? "（本番）" : ""}</td>
                  <td>{g.mission_name ?? "-"}</td>
                  <td>{formatDate(g.created_at)}</td>
                  <td>{g.summary.battles}</td>
                  <td>{g.summary.wins}勝 {g.summary.losses}敗{g.summary.draws ? ` ${g.summary.draws}分` : ""}</td>
                  <td>{g.summary.timeouts}</td>
                  <td><button onClick={() => handlePin(g)}>{g.pinned ? "📌 外す" : "留める"}</button></td>
                  <td><button className="underline" onClick={() => setPicked({ id: g.generation_id, runKey })}>詳細</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SciFiPanel>

      {manifest && (
        <SciFiPanel className="p-4 space-y-4">
          <SciFiHeading level={2}>{manifest.label} の詳細</SciFiHeading>
          <p className="text-xs text-[#00ff41]/60">
            {manifest.generation_id} / ロスター {manifest.roster_name ?? "-"} / 判定する機体 {manifest.player_name ?? "-"} / seed {manifest.seed ?? "-"}
          </p>
          {report ? (
            <>
              <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div><dt className="text-[#00ff41]/60">勝率</dt><dd>{percent(report.wins, report.battles)}（{report.wins}/{report.battles}{report.draws ? `、引き分け ${report.draws}` : ""}）</dd></div>
                <div><dt className="text-[#00ff41]/60">打ち切り</dt><dd>{report.timeouts}</dd></div>
                <div><dt className="text-[#00ff41]/60">平均戦闘時間</dt><dd>{report.elapsed_time.avg.toFixed(1)}s</dd></div>
                <div><dt className="text-[#00ff41]/60">判定機の撃墜数</dt><dd>{report.player_kills}</dd></div>
              </dl>
              {report.objective && (
                <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <div><dt className="text-[#00ff41]/60">作戦</dt><dd>{report.objective.mission_name ?? "-"}</dd></div>
                  <div>
                    <dt className="text-[#00ff41]/60">作戦の成功率</dt>
                    <dd>
                      {percent(report.objective.success, report.objective.battles)}（成功 {report.objective.success} / 失敗 {report.objective.failure} / 引き分け {report.objective.draw}）
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[#00ff41]/60">離脱した友軍（1戦平均）</dt>
                    <dd>
                      {report.objective.battles > 0 ? (report.objective.progress / report.objective.battles).toFixed(1) : "-"}
                      {report.objective.total > 0 ? ` / ${report.objective.total}` : ""}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[#00ff41]/60">撃破された友軍（合計）</dt>
                    <dd>{report.objective.lost}</dd>
                  </div>
                </dl>
              )}
              {report.warnings.length > 0 && (
                <ul className="text-xs text-[#ffb000] list-disc pl-4">
                  {report.warnings.map((w) => <li key={w}>{w}</li>)}
                </ul>
              )}
              <table className="w-full text-xs">
                <thead><tr className="text-left text-[#00ff41]/60"><th>機体</th><th>パイロット</th><th>撃墜数</th><th>被撃墜数</th><th>被撃墜率</th></tr></thead>
                <tbody>
                  {report.units.map((u) => (
                    <tr key={u.unit_id}>
                      <td>{u.is_player ? "★ " : ""}{u.name}</td>
                      <td>{u.pilot_name ?? "-"}</td>
                      <td>{u.kills}</td>
                      <td>{u.deaths}</td>
                      <td>{percent(u.deaths, u.battles)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p className="text-xs text-[#ffb000]">
              report.json がありません。`python -m scripts.simulation.local_sim report {manifest.generation_id}` で作成できます。
            </p>
          )}
          <table className="w-full text-xs">
            <thead><tr className="text-left text-[#00ff41]/60"><th>#</th><th>勝敗</th><th>撃墜</th><th>経過時間</th><th>seed</th><th /></tr></thead>
            <tbody>
              {manifest.battles.map((b) => (
                <tr key={b.index}>
                  <td>{b.index}</td>
                  <td>{b.win_loss}{b.timed_out ? "（打ち切り）" : ""}</td>
                  <td>{b.kills}</td>
                  <td>{b.elapsed_time.toFixed(1)}s</td>
                  <td>{b.seed ?? "-"}</td>
                  <td>
                    <a className="underline" href={battleViewerUrl(manifest.generation_id, b.index)} target="_blank" rel="noopener noreferrer">再生</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </SciFiPanel>
      )}
    </main>
  );
}
