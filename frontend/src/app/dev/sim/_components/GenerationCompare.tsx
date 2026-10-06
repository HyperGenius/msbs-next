/* frontend/src/app/dev/sim/_components/GenerationCompare.tsx */
"use client";

import { ReactNode } from "react";
import { LOCAL_SIM_REPORT_SCHEMA_VERSION, LocalSimManifest, LocalSimReport } from "@/types/battle";
import { useLocalSimReport } from "@/services/api";
import { compareConditions, compareReports, compareUnits } from "@/utils/localSimAnalysis";

interface GenerationCompareProps {
  generations: LocalSimManifest[];
  a: LocalSimManifest;
  b: LocalSimManifest;
  onChange: (a: string, b: string) => void;
}

/** 2つの世代の実行条件と集計値（report.json）を並べ、差（B − A）を表示する。 */
export default function GenerationCompare({ generations, a, b, onChange }: GenerationCompareProps) {
  const reportA = useLocalSimReport(a.generation_id);
  const reportB = useLocalSimReport(b.generation_id);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-3 sm:grid-cols-2">
        <GenerationSelect
          name="A（比べる元）"
          generations={generations}
          value={a.generation_id}
          onChange={(id) => onChange(id, b.generation_id)}
        />
        <GenerationSelect
          name="B（比べる先）"
          generations={generations}
          value={b.generation_id}
          onChange={(id) => onChange(a.generation_id, id)}
        />
      </div>

      <ConditionsTable a={a} b={b} />

      {[
        { name: "A", manifest: a, state: reportA },
        { name: "B", manifest: b, state: reportB },
      ].map(({ name, manifest, state }) => (
        <ReportStatus key={name} name={name} manifest={manifest} {...state} />
      ))}

      {isCurrent(reportA.report) && isCurrent(reportB.report) && (
        <>
          <SummaryTable a={reportA.report} b={reportB.report} />
          <UnitsTable a={reportA.report} b={reportB.report} />
          <Warnings a={reportA.report} b={reportB.report} />
        </>
      )}
    </div>
  );
}

function isCurrent(report: LocalSimReport | undefined): report is LocalSimReport {
  return report?.schema_version === LOCAL_SIM_REPORT_SCHEMA_VERSION;
}

function GenerationSelect({
  name,
  generations,
  value,
  onChange,
}: {
  name: string;
  generations: LocalSimManifest[];
  value: string;
  onChange: (generationId: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-gray-400">
      {name}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm text-green-300"
      >
        {generations.map((g) => (
          <option key={g.generation_id} value={g.generation_id}>
            {g.pinned ? "📌 " : ""}
            {g.label} · {new Date(g.created_at).toLocaleString("ja-JP")} · {g.summary.battles}戦
          </option>
        ))}
      </select>
    </label>
  );
}

/** report.json が無い・古い世代に、CLI での作り直し方を案内する */
function ReportStatus({
  name,
  manifest,
  report,
  isLoading,
  isError,
}: {
  name: string;
  manifest: LocalSimManifest;
  report: LocalSimReport | undefined;
  isLoading: boolean;
  isError: (Error & { status?: number }) | undefined;
}) {
  if (isLoading) return <p className="text-gray-400 text-sm">{name} の集計値を読み込み中...</p>;
  if (isError && isError.status !== 404) {
    return (
      <p className="text-red-400 text-sm" role="alert">
        {name} の集計値を読み込めませんでした: {isError.message}
      </p>
    );
  }
  if (isCurrent(report)) return null;
  return (
    <div className="bg-gray-800 border border-yellow-700 rounded p-3 text-sm text-yellow-300">
      <p className="mb-2">
        {name}（{manifest.label}）の集計値（report.json）が
        {report ? "古い形式です" : "ありません"}。backend で次を実行してから、ページを再読み込みしてください。
      </p>
      <pre className="bg-gray-950 border border-gray-700 rounded p-2 text-xs text-green-300 overflow-x-auto">
        {`cd backend\npython -m scripts.simulation.local_sim report ${manifest.generation_id}`}
      </pre>
    </div>
  );
}

const TABLE = "w-full text-xs border-collapse";
const TH = "text-left font-normal text-gray-500 px-2 py-1 border-b border-gray-700";
const TD = "px-2 py-1 border-b border-gray-800";
const NUM = `${TD} text-right tabular-nums`;

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="text-sm font-bold text-gray-400 mb-2">{title}</h2>
      <div className="overflow-x-auto bg-gray-800 border border-gray-700 rounded">{children}</div>
    </section>
  );
}

function ConditionsTable({ a, b }: { a: LocalSimManifest; b: LocalSimManifest }) {
  return (
    <Section title="条件（違う項目は黄色）">
      <table className={TABLE}>
        <thead>
          <tr>
            <th className={TH}></th>
            <th className={TH}>A</th>
            <th className={TH}>B</th>
          </tr>
        </thead>
        <tbody>
          {compareConditions(a, b).map((row) => (
            <tr key={row.label} className={row.differs ? "text-yellow-300" : "text-gray-300"}>
              <td className={`${TD} text-gray-400 whitespace-nowrap`}>{row.label}</td>
              <td className={TD}>{row.a}</td>
              <td className={TD}>{row.b}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

function SummaryTable({ a, b }: { a: LocalSimReport; b: LocalSimReport }) {
  return (
    <Section title={`集計値（A ${a.battles}戦 / B ${b.battles}戦。回数は1戦あたりか割合）`}>
      <table className={TABLE}>
        <thead>
          <tr>
            <th className={TH}></th>
            <th className={`${TH} text-right`}>A</th>
            <th className={`${TH} text-right`}>B</th>
            <th className={`${TH} text-right`}>差 (B−A)</th>
          </tr>
        </thead>
        <tbody className="text-gray-300">
          {compareReports(a, b).map((row) => (
            <tr key={row.label}>
              <td className={`${TD} text-gray-400 whitespace-nowrap`}>{row.label}</td>
              <td className={NUM}>{row.a}</td>
              <td className={NUM}>{row.b}</td>
              <td className={`${NUM} text-green-300`}>{row.diff}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

function UnitsTable({ a, b }: { a: LocalSimReport; b: LocalSimReport }) {
  return (
    <Section title="機体ごとの撃墜数 / 被撃墜率（★ は判定する機体。片方にしかいない機体は -）">
      <table className={TABLE}>
        <thead>
          <tr>
            <th className={TH}>機体</th>
            <th className={`${TH} text-right`}>撃墜/戦 A</th>
            <th className={`${TH} text-right`}>B</th>
            <th className={`${TH} text-right`}>差</th>
            <th className={`${TH} text-right`}>被撃墜率 A</th>
            <th className={`${TH} text-right`}>B</th>
            <th className={`${TH} text-right`}>差</th>
          </tr>
        </thead>
        <tbody className="text-gray-300">
          {compareUnits(a, b).map((row) => (
            <tr key={row.unitId}>
              <td className={`${TD} whitespace-nowrap`}>
                {row.isPlayer && <span className="text-green-300">★ </span>}
                {row.label}
              </td>
              {[...row.kills, ...row.deathRate].map((cell, i) => (
                <td key={i} className={`${NUM} ${i % 3 === 2 ? "text-green-300" : ""}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

/** `run_simulation.py bench` と同じ閾値（BALANCE_WARN_*）で CLI が出した警告 */
function Warnings({ a, b }: { a: LocalSimReport; b: LocalSimReport }) {
  const warnings = [...a.warnings.map((w) => `[A] ${w}`), ...b.warnings.map((w) => `[B] ${w}`)];
  if (warnings.length === 0) return null;
  return (
    <ul className="flex flex-col gap-1 text-xs text-yellow-300">
      {warnings.map((w) => (
        <li key={w}>⚠ {w}</li>
      ))}
    </ul>
  );
}
