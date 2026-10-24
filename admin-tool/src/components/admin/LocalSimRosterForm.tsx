"use client";

import { useState } from "react";
import { useAdminNpcs } from "@/hooks/useAdminNpcs";
import { useAdminPlayerMobileSuits, useAdminPlayers } from "@/hooks/useAdminPlayers";
import { useAdminTheaters } from "@/hooks/useAdminTheaters";
import { rowsToUnitSpecs, type FetchUnitKind, type FetchUnitRow } from "@/lib/localSim/fetchForm";
import type { LocalSimFetchRequest } from "@/types/localSim";
import { SciFiButton } from "@/components/ui";

const inputClass = "w-full bg-black/60 border border-[#00ff41]/40 px-2 py-1 text-sm text-[#00ff41]";

const KIND_LABELS: Record<FetchUnitKind, string> = {
  player: "プレイヤー",
  npc: "NPC",
  ms: "機体ID",
};

type RowChange = Partial<Omit<FetchUnitRow, "key" | "kind">>;

/** プレイヤーを名前で引き、その所有機から出撃機体を選ぶ。 */
function PlayerUnitFields({
  row,
  disabled,
  onChange,
}: {
  row: FetchUnitRow;
  disabled: boolean;
  onChange: (change: RowChange) => void;
}) {
  const [query, setQuery] = useState("");
  const { players, error: playersError } = useAdminPlayers(query);
  const { mobileSuits, error: suitsError, isLoading } = useAdminPlayerMobileSuits(row.pilotId || null);

  return (
    <>
      <input
        className={inputClass}
        placeholder="名前で検索"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={disabled}
      />
      <select
        className={inputClass}
        value={row.pilotId}
        onChange={(e) => onChange({ pilotId: e.target.value, mobileSuitId: "" })}
        disabled={disabled}
      >
        <option value="">{playersError ? "（パイロットを読めません）" : "パイロットを選ぶ"}</option>
        {players.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}（Lv{p.level} / {p.mobile_suit_count}機）
          </option>
        ))}
      </select>
      <select
        className={inputClass}
        value={row.mobileSuitId}
        onChange={(e) => onChange({ mobileSuitId: e.target.value })}
        disabled={disabled || !row.pilotId}
      >
        <option value="">
          {suitsError ? "（所有機を読めません）" : isLoading ? "読み込み中…" : "出撃機体を選ぶ"}
        </option>
        {mobileSuits.map((ms) => (
          <option key={ms.id} value={ms.id}>
            {ms.name}
            {ms.master_mobile_suit_id ? `（${ms.master_mobile_suit_id}）` : ""}
            {ms.is_active ? " ★出撃機体" : ""} / {ms.id.slice(0, 8)}
          </option>
        ))}
      </select>
    </>
  );
}

function NpcUnitFields({
  row,
  disabled,
  onChange,
}: {
  row: FetchUnitRow;
  disabled: boolean;
  onChange: (change: RowChange) => void;
}) {
  const { npcs, isError } = useAdminNpcs();
  return (
    <select
      className={`${inputClass} md:col-span-3`}
      value={row.pilotId}
      onChange={(e) => onChange({ pilotId: e.target.value })}
      disabled={disabled}
    >
      <option value="">{isError ? "（NPC を読めません）" : "NPC のパイロットを選ぶ"}</option>
      {(npcs ?? []).map((npc) => (
        <option key={npc.id} value={npc.id}>
          {npc.name}（Lv{npc.level}{npc.is_ace ? " / エース" : ""}）
        </option>
      ))}
    </select>
  );
}

interface Props {
  /** 既にあるロスター名。同名なら上書きを確認する */
  rosterNames: string[];
  disabled: boolean;
  onSubmit: (request: LocalSimFetchRequest) => Promise<void>;
}

/** `local_sim fetch` の引数を組み立てるフォーム。本番DBには CLI が Read Only で接続する。 */
export default function LocalSimRosterForm({ rosterNames, disabled, onSubmit }: Props) {
  const { theaters, isError: theatersError } = useAdminTheaters();
  const [name, setName] = useState("");
  const [theater, setTheater] = useState("");
  const [minovsky, setMinovsky] = useState("");
  const [npc, setNpc] = useState("0");
  const [ace, setAce] = useState("0");
  const [rows, setRows] = useState<FetchUnitRow[]>([]);
  const [nextKey, setNextKey] = useState(1);
  const [message, setMessage] = useState<string | null>(null);

  const baseMinovsky = theaters?.find((t) => t.id === theater)?.base_minovsky;

  function addRow(kind: FetchUnitKind) {
    setRows((current) => [...current, { key: nextKey, kind, pilotId: "", mobileSuitId: "", team: "" }]);
    setNextKey((key) => key + 1);
  }

  function updateRow(key: number, change: RowChange) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...change } : row)));
  }

  async function handleSubmit() {
    setMessage(null);
    const units = rowsToUnitSpecs(rows);
    if (typeof units === "string") {
      setMessage(units);
      return;
    }
    const rosterName = name.trim();
    const force = rosterName !== "" && rosterNames.includes(rosterName);
    if (force && !window.confirm(`ロスター ${rosterName} は既にあります。上書きしますか？`)) return;
    try {
      await onSubmit({
        ...units,
        npc: Number(npc) || 0,
        ace: Number(ace) || 0,
        theater: theater.trim() || null,
        minovsky: minovsky.trim() === "" ? null : Number(minovsky),
        name: rosterName || null,
        force,
      });
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "ロスターの作成を開始できません。");
    }
  }

  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <label className="space-y-1">
          <span>ロスター名（省略すると日時）</span>
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} disabled={disabled} />
        </label>
        <label className="space-y-1">
          <span>戦域</span>
          {theatersError ? (
            <input
              className={inputClass}
              placeholder="戦域ID（一覧を読めません）"
              value={theater}
              onChange={(e) => setTheater(e.target.value)}
              disabled={disabled}
            />
          ) : (
            <select className={inputClass} value={theater} onChange={(e) => setTheater(e.target.value)} disabled={disabled}>
              <option value="">（戦域なし・宇宙）</option>
              {(theaters ?? []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}（{t.id}）
                </option>
              ))}
            </select>
          )}
        </label>
        <label className="space-y-1">
          <span>ミノフスキー濃度（0〜1、省略可）</span>
          <input
            className={inputClass}
            type="number"
            min={0}
            max={1}
            step={0.05}
            placeholder={baseMinovsky != null ? `戦域の基準 ${baseMinovsky}` : theater ? "戦域の基準" : "0"}
            value={minovsky}
            onChange={(e) => setMinovsky(e.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="space-y-1">
          <span>NPC 数（本番の永続化NPC。不足分は生成）</span>
          <input className={inputClass} type="number" min={0} value={npc} onChange={(e) => setNpc(e.target.value)} disabled={disabled} />
        </label>
        <label className="space-y-1">
          <span>エース数</span>
          <input className={inputClass} type="number" min={0} value={ace} onChange={(e) => setAce(e.target.value)} disabled={disabled} />
        </label>
      </div>

      <div className="space-y-2">
        <p>参加機体（チーム名が同じ機体は味方。空欄は個人戦）</p>
        {rows.length === 0 && <p className="text-xs text-[#00ff41]/60">参加機体を追加してください（NPC 数・エース数だけでも作れます）。</p>}
        {rows.map((row) => (
          <div key={row.key} className="grid grid-cols-1 md:grid-cols-[6rem_1fr_1fr_1fr_8rem_auto] gap-2 items-center">
            <span className="text-xs text-[#00ff41]/70">{KIND_LABELS[row.kind]}</span>
            {row.kind === "player" && (
              <PlayerUnitFields row={row} disabled={disabled} onChange={(change) => updateRow(row.key, change)} />
            )}
            {row.kind === "npc" && (
              <NpcUnitFields row={row} disabled={disabled} onChange={(change) => updateRow(row.key, change)} />
            )}
            {row.kind === "ms" && (
              <input
                className={`${inputClass} md:col-span-3`}
                placeholder="機体ID（UUID）"
                value={row.mobileSuitId}
                onChange={(e) => updateRow(row.key, { mobileSuitId: e.target.value })}
                disabled={disabled}
              />
            )}
            <input
              className={inputClass}
              placeholder="チーム（省略可）"
              value={row.team}
              onChange={(e) => updateRow(row.key, { team: e.target.value })}
              disabled={disabled}
            />
            <button
              className="text-xs text-red-400 hover:underline"
              onClick={() => setRows((current) => current.filter((r) => r.key !== row.key))}
              disabled={disabled}
            >
              削除
            </button>
          </div>
        ))}
        <div className="flex gap-2">
          {(Object.keys(KIND_LABELS) as FetchUnitKind[]).map((kind) => (
            <SciFiButton key={kind} size="sm" variant="secondary" onClick={() => addRow(kind)} disabled={disabled}>
              + {KIND_LABELS[kind]}
            </SciFiButton>
          ))}
        </div>
      </div>

      {message && <p className="text-red-400">{message}</p>}
      <SciFiButton onClick={handleSubmit} disabled={disabled}>
        {disabled ? "実行中…" : "ロスターを作成"}
      </SciFiButton>
    </div>
  );
}
