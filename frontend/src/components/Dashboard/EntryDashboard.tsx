/* frontend/src/components/Dashboard/EntryDashboard.tsx */
"use client";

import { useState } from "react";
import { MobileSuit } from "@/types/battle";
import { getRankColor } from "@/utils/rankUtils";
import { STATUS_LABELS } from "@/utils/displayUtils";
import MobileSuitRankBadges from "./MobileSuitRankBadges";

interface EntryDashboardProps {
  isEntered: boolean;
  entryCount: number;
  mobileSuit?: MobileSuit;
  onEntry: () => void;
  onCancel: () => void;
  isLoading: boolean;
  disabled?: boolean;
}

/*
 * エントリー状況を表示するダッシュボードコンポーネント
  * - エントリー済みの場合は機体情報と参加者数、キャンセルボタンを表示
  * - 未エントリーの場合はエントリーボタンと参加者数を表示
*/
export default function EntryDashboard({
  isEntered,
  entryCount,
  mobileSuit,
  onEntry,
  onCancel,
  isLoading,
  disabled = false,
}: EntryDashboardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (isEntered && mobileSuit) {
    return (
      <div className="space-y-3">
        {/* エントリー確認ステータス */}
        <div className="bg-[#0a0a0a] border-2 border-[#00ff41]/50 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-[#00ff41] rounded-full animate-pulse"></div>
              <span className="text-[#00ff41] font-bold font-mono text-sm tracking-widest">
                ENTRY CONFIRMED
              </span>
            </div>
            <span className="text-xs text-[#00ff41]/50 font-mono border border-[#00ff41]/30 px-2 py-0.5">
              ✓ エントリー完了
            </span>
          </div>

          {/* 機体名 + ランクバッジ */}
          <div className="space-y-2">
            <div className="flex items-baseline gap-3">
              <span className="text-[#00ff41]/50 font-mono text-xs">機体名</span>
              <span className="text-white font-bold font-mono">{mobileSuit.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#00ff41]/50 font-mono text-xs">Specs</span>
              <MobileSuitRankBadges mobileSuit={mobileSuit} />
            </div>
          </div>

          {/* アコーディオン：詳細パラメータ */}
          {/* 将来的にパイロットパラメータと統合したレーダーチャート表示でも面白いかもしれない */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            className="w-full flex items-center justify-between px-3 py-2 mt-3 text-xs font-mono text-[#00ff41]/50 border border-[#00ff41]/20 hover:border-[#00ff41]/50 hover:text-[#00ff41]/80 transition-colors no-min-size"
          >
            <span>詳細パラメータを展開</span>
            <span>{isExpanded ? "▲" : "▼"}</span>
          </button>

          {isExpanded && (
            <div className="mt-2 bg-[#050505] border border-[#00ff41]/20 p-3 font-mono text-xs">
              {/* 機体の詳細パラメータ,ランクバッジと情報が重複しているため改善が必要 */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                <div>
                  <span className="text-[#00ff41]/50">{STATUS_LABELS.hp}:</span>{" "}
                  {mobileSuit.hp_rank && (
                    <span className={`ml-1 ${getRankColor(mobileSuit.hp_rank)}`}>
                      {mobileSuit.hp_rank}
                    </span>
                  )}
                </div>
                <div>
                  <span className="text-[#00ff41]/50">{STATUS_LABELS.armor}:</span>{" "}
                  {mobileSuit.armor_rank && (
                    <span className={`ml-1 ${getRankColor(mobileSuit.armor_rank)}`}>
                      {mobileSuit.armor_rank}
                    </span>
                  )}
                </div>
                <div>
                  <span className="text-[#00ff41]/50">{STATUS_LABELS.mobility}:</span>{" "}
                  {mobileSuit.mobility_rank && (
                    <span className={`ml-1 ${getRankColor(mobileSuit.mobility_rank)}`}>
                      {mobileSuit.mobility_rank}
                    </span>
                  )}
                </div>
              </div>

              {/* パイロットパラメータを表示する予定, 機体詳細パラメータ整理のタイミングで改修 */}

              {/* 機体の武装表示 */}
              {mobileSuit.weapons && mobileSuit.weapons.length > 0 && (
                <div className="mt-2 pt-2 border-t border-[#00ff41]/10">
                  <span className="text-[#00ff41]/50 block mb-1">武装:</span>
                  {mobileSuit.weapons.map((w) => (
                    <div key={w.id} className="text-[#00ff41]/70 ml-2 py-0.5">
                      {w.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 参加者数 */}
        <div className="bg-[#0a0a0a] border border-[#00ff41]/20 p-3 flex items-center justify-between font-mono text-xs">
          <span className="text-[#00ff41]/50">現在の参加エントリー数</span>
          <span className="text-[#00ff41] font-bold text-lg">
            {entryCount} <span className="text-[#00ff41]/40 text-xs">機</span>
          </span>
        </div>

        {/* キャンセルボタン */}
        <button
          onClick={onCancel}
          disabled={isLoading}
          className={`w-full px-6 py-3 font-bold font-mono text-sm transition-colors border-2 ${
            isLoading
              ? "bg-gray-700 cursor-not-allowed text-gray-500 border-gray-600"
              : "bg-transparent text-red-400 border-red-500/50 hover:border-red-500 hover:bg-red-900/20"
          }`}
        >
          {isLoading ? "処理中..." : "エントリーをキャンセル"}
        </button>
      </div>
    );
  }

  // 未エントリー時
  return (
    <div className="space-y-3">
      {/* エントリーボタン */}
      <div className="bg-[#0a0a0a] border-2 border-[#00ff41]/20 p-6 text-center">
        <div className="mb-5">
          <h3 className="text-sm font-bold font-mono text-[#00ff41]/70 mb-1 tracking-widest">
            次回バトルへの参加登録
          </h3>
          <p className="text-xs text-[#00ff41]/40 font-mono">
            エントリーすると次回の定期バトルに参加できます
          </p>
        </div>

        <button
          onClick={onEntry}
          disabled={isLoading || disabled}
          className={`w-full px-8 py-4 font-bold font-mono text-lg border-2 transition-all ${
            isLoading || disabled
              ? "bg-gray-700 cursor-not-allowed text-gray-500 border-gray-600"
              : "bg-[#00ff41] text-black border-[#00ff41] hover:bg-[#00cc33] hover:border-[#00cc33] sf-glow-green"
          }`}
        >
          {isLoading ? "処理中..." : "▶ 出撃確定"}
        </button>

        {disabled && (
          <p className="text-xs text-[#ffb000]/70 font-mono mt-3">
            ※ エントリーするには機体が必要です
          </p>
        )}
      </div>

      {/* 参加者数 */}
      <div className="bg-[#0a0a0a] border border-[#00ff41]/20 p-3 font-mono">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-[#00ff41]/50">👥 現在の参加者</span>
          <span className="text-[#00f0ff] font-bold text-xl">{entryCount}</span>
        </div>
        <div className="h-1.5 bg-[#050505] border border-[#00ff41]/10 overflow-hidden">
          <div
            className="h-full bg-[#00ff41]/60 transition-all duration-500"
            style={{ width: `${Math.min(entryCount * 10, 100)}%` }}
          ></div>
        </div>
      </div>
    </div>
  );
}

