"use client";

import { MobileSuit } from "@/types/battle";

interface EntryDashboardProps {
  isEntered: boolean;
  entryCount: number;
  mobileSuit?: MobileSuit;
  onEntry: () => void;
  onCancel: () => void;
  isLoading: boolean;
  disabled?: boolean;
}

export default function EntryDashboard({
  isEntered,
  entryCount,
  mobileSuit,
  onEntry,
  onCancel,
  isLoading,
  disabled = false,
}: EntryDashboardProps) {
  if (isEntered && mobileSuit) {
    return (
      <div className="space-y-4">
        {/* エントリー済みステータス */}
        <div className="bg-green-900/30 border-2 border-green-500 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
              <h3 className="text-2xl font-bold text-green-300">
                ENTRY CONFIRMED
              </h3>
            </div>
            <div className="text-sm text-green-400 px-3 py-1 bg-green-900/50 rounded border border-green-700">
              ✓ エントリー済み
            </div>
          </div>

          {/* 使用機体情報 */}
          <div className="bg-gray-800/70 rounded-lg p-4 border border-green-700">
            <p className="text-xs text-gray-400 mb-2">使用機体</p>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xl font-bold text-white mb-1">
                  {mobileSuit.name}
                </p>
                <div className="flex gap-4 text-sm text-gray-300">
                  <span>HP: {mobileSuit.max_hp}</span>
                  <span>装甲: {mobileSuit.armor}</span>
                  <span>機動: {mobileSuit.mobility}</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-green-900/50 rounded border-2 border-green-500 flex items-center justify-center">
                <span className="text-2xl">🤖</span>
              </div>
            </div>
          </div>
        </div>

        {/* 参加者数表示 */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">現在の参加エントリー数</span>
            <span className="text-2xl font-bold text-green-400">
              {entryCount} <span className="text-sm text-gray-500">機</span>
            </span>
          </div>
        </div>

        {/* キャンセルボタン */}
        <button
          onClick={onCancel}
          disabled={isLoading}
          className={`w-full px-6 py-3 rounded font-bold transition-colors ${
            isLoading
              ? "bg-gray-500 cursor-not-allowed text-gray-300"
              : "bg-red-700 hover:bg-red-600 text-white border border-red-500"
          }`}
        >
          {isLoading ? "処理中..." : "エントリーをキャンセル"}
        </button>
      </div>
    );
  }

  // 未エントリー時
  return (
    <div className="space-y-4">
      {/* エントリーボタン */}
      <div className="bg-gray-800/50 border-2 border-gray-700 rounded-lg p-8 text-center">
        <div className="mb-6">
          <h3 className="text-xl font-bold text-gray-300 mb-2">
            次回バトルへの参加登録
          </h3>
          <p className="text-sm text-gray-500">
            エントリーすると次回の定期バトルに参加できます
          </p>
        </div>

        <button
          onClick={onEntry}
          disabled={isLoading || disabled}
          className={`w-full px-12 py-6 rounded-lg font-bold text-2xl transition-all shadow-lg ${
            isLoading || disabled
              ? "bg-gray-600 cursor-not-allowed text-gray-400"
              : "bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-400 hover:to-blue-400 text-white hover:shadow-green-500/50 transform hover:scale-105"
          }`}
        >
          {isLoading ? "処理中..." : "⚡ ENTRY ⚡"}
        </button>

        {disabled && (
          <p className="text-xs text-yellow-500 mt-3">
            ※ エントリーするには機体が必要です
          </p>
        )}
      </div>

      {/* 参加者数表示 */}
      <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 rounded-lg p-4 border border-blue-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-blue-300">👥 現在の参加者</span>
          </div>
          <span className="text-3xl font-bold text-blue-400">
            {entryCount}
          </span>
        </div>
        <div className="mt-2 h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
            style={{ 
              // プログレスバーは参加者10人で100%になるように設定
              width: `${Math.min(entryCount * 10, 100)}%` 
            }}
          ></div>
        </div>
      </div>
    </div>
  );
}
