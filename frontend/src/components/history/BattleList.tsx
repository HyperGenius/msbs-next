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
    <div className="max-w-2xl mx-auto w-full h-full flex flex-col min-h-0">
      {/*
        History ページ自体はスクロールさせず（main側で二重スクロールになるため）、
        この Records カード内だけを flex-1 + overflow-y-auto でスクロール領域にする。
      */}
      <div className="bg-gray-800 border border-green-800 rounded-lg flex-1 min-h-0 overflow-y-auto">
        {/*
          コンテナ側に上paddingを付けると、sticky見出しはそのpadding分だけ
          下にずれた位置で止まるため、paddingの隙間をスクロール中のカードが
          突き抜けて見えてしまう（Issue #415で発生）。paddingは見出し自身に
          持たせ、見出しをコンテナの最上端に完全密着させて隙間を無くす。
        */}
        <h2 className="text-xl font-bold sticky top-0 z-10 bg-gray-800 px-4 pt-4 pb-4">
          Records
        </h2>
        <div className="space-y-2 px-4 pb-4">
          {battles.map((battle) => {
            const hasDigest = battle.digest_text != null;
            // 辛勝タグは「土壇場で耐えた」ドラマを強調するため、枠と背景を警告色にする
            const isCritical = battle.digest_tag === "辛勝";

            return (
              <button
                key={battle.id}
                onClick={() => onSelectBattle(battle)}
                className={`w-full text-left p-4 rounded border-2 transition-all ${
                  isCritical
                    ? "border-orange-600/70 bg-red-950/20 hover:border-orange-500"
                    : "border-gray-700 hover:border-green-700"
                }`}
              >
                <div className="flex justify-between items-start">
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
                <p className="text-xs text-gray-500 mb-2">
                  {new Date(battle.created_at).toLocaleString("ja-JP")}
                </p>
                {hasDigest ? (
                  <>
                    <div className="border-t border-dashed border-gray-700 pt-2 mb-2">
                      <p className="text-sm">
                        <span
                          className={`font-bold ${
                            battle.player_survived ? "text-green-300" : "text-red-400"
                          }`}
                        >
                          {battle.player_survived ? "生還" : "撃墜"}
                        </span>
                        <span className="text-gray-600 mx-1">/</span>
                        <span className="text-gray-500">撃破</span>{" "}
                        <span className="font-bold">{battle.kills ?? 0}機</span>
                        {isCritical ? (
                          <>
                            <span className="text-gray-600 mx-1">/</span>
                            <span className="text-gray-500">HP最低</span>{" "}
                            <span className="font-bold text-orange-400">
                              {battle.min_hp_percent}%
                            </span>
                          </>
                        ) : null}
                        <span className="text-gray-600 mx-1">/</span>
                        <span className="text-gray-500">搭乗MS</span>{" "}
                        <span className="font-bold">{battle.pilot_ms_name}</span>
                      </p>
                      <p className="text-sm mt-1">
                        <span className="text-gray-500">獲得Credits</span>{" "}
                        <span className="font-bold text-yellow-300">
                          {(battle.credits_gained ?? 0).toLocaleString()}
                        </span>
                        <span className="text-gray-600 mx-1">/</span>
                        <span className="text-gray-500">獲得Exp</span>{" "}
                        <span className="font-bold text-cyan-300">
                          {(battle.exp_gained ?? 0).toLocaleString()}
                        </span>
                      </p>
                    </div>
                    <p className="text-sm text-green-300 italic">「{battle.digest_text}」</p>
                  </>
                ) : null}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
