/* frontend/src/components/history/BattleList.tsx */
"use client";

import { BattleResult } from "@/types/battle";

/**
 * バトル履歴リストを表示するためのプロパティ
 * @property battles - バトル結果の配列
 * @property isLoading - データの読み込み中かどうか
 * @property isError - データの読み込みに失敗したかどうか
 * @property onSelectBattle - バトルが選択されたときのコールバック関数
 * @property getMissionName - ミッションIDからミッション名を取得する関数
 */
interface BattleListProps {
  battles: BattleResult[];
  isLoading: boolean;
  isError: boolean;
  onSelectBattle: (battle: BattleResult) => void;
  getMissionName: (missionId: number | null, createdAt?: string) => string;
}

/**
 * バトル履歴の一覧を表示するコンポーネント
 * 読み込み中、エラー、データなし、データありの各状態に応じたUIを提供します。
 */
export default function BattleList({
  battles,
  isLoading,
  isError,
  onSelectBattle,
  getMissionName,
}: BattleListProps) {
  if (isLoading) {
    return (
      <div className="text-center py-12">
        <p className="text-xl">Loading battle history...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-900/30 border border-red-500 p-4 rounded">
        <p className="text-red-400">Failed to load battle history. Check if backend is running.</p>
      </div>
    );
  }

  if (battles.length === 0) {
    return (
      <div className="bg-gray-800 border border-gray-700 p-8 rounded text-center">
        <p className="text-xl text-gray-400">No battle records found.</p>
        <p className="text-sm text-gray-500 mt-2">Complete some missions to see your history here.</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-gray-800 border border-green-800 rounded-lg p-4 max-h-[800px] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4 sticky top-0 bg-gray-800 pb-2">Records</h2>
        <div className="space-y-2">
          {battles.map((battle) => (
            <button
              key={battle.id}
              onClick={() => onSelectBattle(battle)}
              className="w-full text-left p-4 rounded border-2 border-gray-700 hover:border-green-700 transition-all"
            >
              <div className="flex justify-between items-start mb-2">
                <span className="font-bold">{getMissionName(battle.mission_id, battle.created_at)}</span>
                <span
                  className={`px-2 py-1 rounded text-xs font-bold ${
                    battle.win_loss === "WIN"
                      ? "bg-green-900 text-green-300"
                      : battle.win_loss === "LOSE"
                      ? "bg-red-900 text-red-300"
                      : "bg-yellow-900 text-yellow-300"
                  }`}
                >
                  {battle.win_loss}
                </span>
              </div>
              <p className="text-xs text-gray-400">
                {new Date(battle.created_at).toLocaleString("ja-JP")}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Turns: {battle.logs.length > 0 ? battle.logs[battle.logs.length - 1].turn : 0}
              </p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
