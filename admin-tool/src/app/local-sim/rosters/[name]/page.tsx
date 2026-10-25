"use client";

import { use, useState } from "react";
import Link from "next/link";
import { saveLocalSimRoster, useLocalSimRoster } from "@/hooks/useLocalSim";
import { duplicateEntry } from "@/lib/localSim/rosterEdit";
import { isValidName } from "@/lib/localSim/shared";
import type { LocalSimMissionMaster, LocalSimRoster, LocalSimRosterEntry } from "@/types/localSim";
import { SciFiButton, SciFiHeading, SciFiPanel } from "@/components/ui";
import RosterConditionsEditor from "@/components/admin/RosterConditionsEditor";
import RosterEntryEditor from "@/components/admin/RosterEntryEditor";
import RosterMissionEditor from "@/components/admin/RosterMissionEditor";
import { missionMasterError } from "@/lib/localSim/missionEdit";

type Snapshot = Record<string, unknown>;

interface EntryItem {
  key: string;
  /** 編集を始める時点の機体。複製した機体は複製元の値 */
  entry: LocalSimRosterEntry;
  /** 元のロスターの機体。複製した機体は null */
  original: LocalSimRosterEntry | null;
  /** 編集後のスナップショット。入力が不正なときは null */
  snapshot: Snapshot | null;
}

const inputClass = "w-full bg-black/60 border border-[#00ff41]/40 px-2 py-1 text-sm text-[#00ff41]";

function entryTitle(entry: LocalSimRosterEntry, snapshot: Snapshot | null): string {
  const name = String(snapshot?.name ?? entry.snapshot.name ?? "-");
  return `${name}（${entry.source.pilot_name ?? entry.source.kind}${entry.snapshot.team_id ? ` / チーム ${entry.snapshot.team_id}` : ""}）`;
}

function RosterEditor({ source }: { source: LocalSimRoster }) {
  const [items, setItems] = useState<EntryItem[]>(() =>
    source.entries.map((entry, i) => ({ key: `entry-${i}`, entry, original: entry, snapshot: entry.snapshot }))
  );
  const [nextKey, setNextKey] = useState(0);
  const [conditions, setConditions] = useState(source.conditions);
  const [mission, setMission] = useState<LocalSimMissionMaster | null>(source.mission?.master ?? null);
  const [saveName, setSaveName] = useState(`${source.name}-edit`);
  const [force, setForce] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  function setSnapshot(key: string, snapshot: Snapshot | null) {
    setItems((current) => current.map((item) => (item.key === key && item.snapshot !== snapshot ? { ...item, snapshot } : item)));
  }

  function duplicate(item: EntryItem) {
    const copy = duplicateEntry({ ...item.entry, snapshot: item.snapshot ?? item.entry.snapshot });
    setNextKey(nextKey + 1);
    setItems((current) => {
      const index = current.findIndex((i) => i.key === item.key);
      const added: EntryItem = { key: `entry-new-${nextKey}`, entry: copy, original: null, snapshot: copy.snapshot };
      return [...current.slice(0, index + 1), added, ...current.slice(index + 1)];
    });
  }

  const density = conditions.minovsky_density;
  const error =
    (!isValidName(saveName) && "ロスター名は英数字で始め、英数字と _ . - だけを使ってください。") ||
    (items.some((i) => i.snapshot === null) && "入力が不正な機体があります。赤い項目を直してください。") ||
    (items.length === 0 && !mission && "機体が 1 機もありません。") ||
    (!(density >= 0 && density <= 1) && "ミノフスキー濃度は 0〜1 にしてください。") ||
    (mission && missionMasterError(mission)) ||
    null;

  async function save() {
    const roster: LocalSimRoster = {
      ...source,
      name: saveName,
      conditions,
      entries: items.map((item) => ({ ...item.entry, snapshot: item.snapshot ?? item.entry.snapshot })),
      mission: source.mission && mission ? { ...source.mission, master: mission } : source.mission,
    };
    setSaving(true);
    setMessage(null);
    try {
      await saveLocalSimRoster(saveName, roster, force);
      setMessage({ kind: "ok", text: `ロスター ${saveName} を保存しました。` });
    } catch (e) {
      setMessage({ kind: "error", text: e instanceof Error ? e.message : "保存に失敗しました。" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <SciFiPanel className="p-4 space-y-3">
        <SciFiHeading level={2}>戦域の条件</SciFiHeading>
        <RosterConditionsEditor conditions={conditions} original={source.conditions} onChange={setConditions} />
      </SciFiPanel>

      <SciFiPanel className="p-4 space-y-3">
        <SciFiHeading level={2}>機体（{items.length} 機）</SciFiHeading>
        {items.length === 0 && <p className="text-xs text-[#00ff41]/50">機体がありません</p>}
        {items.map((item) => (
          <details key={item.key} className="border border-[#00ff41]/30" open={items.length === 1}>
            <summary className="cursor-pointer px-3 py-2 text-sm flex items-center gap-2">
              <span className="flex-1">{entryTitle(item.entry, item.snapshot)}</span>
              {!item.original && <span className="text-xs text-[#ffb000]">追加した機体</span>}
              {item.snapshot === null && <span className="text-xs text-red-400">入力エラー</span>}
            </summary>
            <div className="p-3 space-y-3">
              <RosterEntryEditor
                initial={item.entry.snapshot}
                original={item.original?.snapshot ?? null}
                idPrefix={`roster_${item.key}`}
                onChange={(snapshot) => setSnapshot(item.key, snapshot)}
              />
              <div className="flex gap-3 text-xs">
                <button type="button" onClick={() => duplicate(item)} className="text-[#00ff41]/70 hover:underline">
                  この機体を複製
                </button>
                <button
                  type="button"
                  onClick={() => setItems((current) => current.filter((i) => i.key !== item.key))}
                  className="text-red-400 hover:underline"
                >
                  この機体を外す
                </button>
              </div>
            </div>
          </details>
        ))}
      </SciFiPanel>

      {mission && (
        <SciFiPanel className="p-4 space-y-3">
          <SciFiHeading level={2}>作戦: {String(source.mission?.master.name ?? "")}</SciFiHeading>
          <RosterMissionEditor master={source.mission!.master} onChange={setMission} />
        </SciFiPanel>
      )}

      <SciFiPanel className="p-4 space-y-3">
        <SciFiHeading level={2}>名前を付けて保存</SciFiHeading>
        <p className="text-xs text-[#00ff41]/60">
          新しいロスターとして保存します。元のロスター（{source.name}）は、上書きにチェックを入れない限り変えません。
          本番DBには書き込みません。
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <label className="space-y-1">
            <span>保存するロスター名</span>
            <input className={inputClass} value={saveName} onChange={(e) => setSaveName(e.target.value)} />
          </label>
          <label className="flex items-end gap-2 pb-1">
            <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
            <span>同名のロスターを上書きする</span>
          </label>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        {message && (
          <p className={`text-sm ${message.kind === "ok" ? "text-[#00ff41]" : "text-red-400"}`}>
            {message.text}
            {message.kind === "ok" && (
              <>
                {" "}
                <Link href="/local-sim" className="underline">
                  実行画面へ
                </Link>
                で元のロスターと同じシードで実行し、/dev/sim の比較で差を確かめます。
              </>
            )}
          </p>
        )}
        <SciFiButton onClick={save} disabled={saving || !!error}>
          {saving ? "保存中..." : "保存"}
        </SciFiButton>
      </SciFiPanel>
    </div>
  );
}

export default function LocalSimRosterEditPage({ params }: { params: Promise<{ name: string }> }) {
  const { name } = use(params);
  const { roster, error, isLoading } = useLocalSimRoster(name);

  return (
    <main className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <SciFiHeading level={1}>ロスターの編集: {name}</SciFiHeading>
        <Link href="/local-sim" className="text-sm text-[#00ff41]/70 hover:underline">
          ← ローカルシミュレータ
        </Link>
      </div>
      <p className="text-xs text-[#00ff41]/60">
        機体・戦域・作戦の値を変えて、新しいロスターとして保存します。変えた値は琥珀色で示します。
        機体の入力欄は NPC 機の編集と同じで、管理API（backend）から機体マスターなどを引きます。
      </p>
      {isLoading && <p className="text-sm text-[#ffb000] animate-pulse">読み込み中...</p>}
      {error && <p className="text-sm text-red-400">ロスターを読めません。`next dev` で起動しているか、ロスター名を確認してください。</p>}
      {roster && <RosterEditor key={name} source={roster} />}
    </main>
  );
}
