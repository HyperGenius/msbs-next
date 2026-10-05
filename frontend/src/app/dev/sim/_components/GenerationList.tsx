/* frontend/src/app/dev/sim/_components/GenerationList.tsx */
"use client";

import { LocalSimManifest } from "@/types/battle";

interface GenerationListProps {
  generations: LocalSimManifest[];
  selectedId: string | null;
  onSelect: (generationId: string) => void;
}

const COMMIT_DIGITS = 7;

/** 世代を新しい順に、日時・ラベル・戦闘数・勝敗・ピン留めで並べる。 */
export default function GenerationList({ generations, selectedId, onSelect }: GenerationListProps) {
  return (
    <section>
      <h2 className="text-sm font-bold text-gray-400 mb-2">世代</h2>
      <ul className="flex flex-col gap-2">
        {generations.map((g) => {
          const selected = g.generation_id === selectedId;
          return (
            <li key={g.generation_id}>
              <button
                type="button"
                onClick={() => onSelect(g.generation_id)}
                aria-pressed={selected}
                className={`w-full text-left rounded border px-3 py-2 transition-colors ${
                  selected
                    ? "border-green-500 bg-green-900/30"
                    : "border-gray-700 bg-gray-800 hover:border-green-700"
                }`}
              >
                <div className="flex items-center gap-2">
                  {g.pinned && <span title="ピン留め">📌</span>}
                  <span className="font-bold text-green-300 truncate">{g.label}</span>
                </div>
                <div className="text-xs text-gray-400">
                  {new Date(g.created_at).toLocaleString("ja-JP")}
                </div>
                <div className="text-xs text-gray-300 mt-1">
                  {g.summary.battles}戦 {g.summary.wins}勝{g.summary.losses}敗
                  {g.summary.timeouts > 0 && ` (打ち切り${g.summary.timeouts})`} · 撃墜{g.summary.total_kills}
                </div>
                <div className="text-[10px] text-gray-500 truncate">
                  {g.roster_name}
                  {g.git.commit && ` · ${g.git.commit.slice(0, COMMIT_DIGITS)}${g.git.dirty ? " (dirty)" : ""}`}
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
