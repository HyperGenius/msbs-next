/* frontend/src/app/dev/sim/_components/SimBattleList.tsx */
"use client";

import { LocalSimBattleSummary } from "@/types/battle";

interface SimBattleListProps {
  battles: LocalSimBattleSummary[];
  selectedIndex: number | null;
  onSelect: (index: number) => void;
}

/** 世代のバトルを、勝敗・経過時間・シードで並べる。 */
export default function SimBattleList({ battles, selectedIndex, onSelect }: SimBattleListProps) {
  return (
    <section>
      <h2 className="text-sm font-bold text-gray-400 mb-2">バトル</h2>
      <ul className="flex flex-col gap-1">
        {battles.map((b) => {
          const selected = b.index === selectedIndex;
          return (
            <li key={b.index}>
              <button
                type="button"
                onClick={() => onSelect(b.index)}
                aria-pressed={selected}
                className={`w-full grid grid-cols-[2.5rem_3.5rem_1fr_auto] items-center gap-2 rounded border px-3 py-1.5 text-xs text-left transition-colors ${
                  selected
                    ? "border-green-500 bg-green-900/30"
                    : "border-gray-700 bg-gray-800 hover:border-green-700"
                }`}
              >
                <span className="text-gray-400">#{b.index}</span>
                <span className={b.win_loss === "WIN" ? "text-green-300 font-bold" : "text-red-300 font-bold"}>
                  {b.win_loss}
                </span>
                <span className="text-gray-300">
                  {b.elapsed_time.toFixed(1)}秒 · 撃墜{b.kills}
                  {b.timed_out && <span className="text-yellow-400"> · 打ち切り</span>}
                </span>
                <span className="text-gray-500">seed {b.seed}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
