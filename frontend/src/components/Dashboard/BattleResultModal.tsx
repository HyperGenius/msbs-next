"use client";

import { useState, useEffect } from "react";
import { BattleRewards } from "@/types/battle";

interface BattleResultModalProps {
  winLoss: "WIN" | "LOSE" | "DRAW";
  rewards: BattleRewards | null;
  onClose: () => void;
}

export default function BattleResultModal({
  winLoss,
  rewards,
  onClose,
}: BattleResultModalProps) {
  const [showContent, setShowContent] = useState(false);
  const [animatedExp, setAnimatedExp] = useState(0);
  const [animatedCredits, setAnimatedCredits] = useState(0);

  useEffect(() => {
    // コンテンツ表示のディレイ
    const timer = setTimeout(() => setShowContent(true), 300);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!rewards || !showContent) return;

    // 経験値のカウントアップアニメーション
    const expDuration = 1500;
    const expSteps = 30;
    const expIncrement = rewards.exp_gained / expSteps;
    let expCount = 0;

    const expInterval = setInterval(() => {
      expCount++;
      if (expCount >= expSteps) {
        setAnimatedExp(rewards.exp_gained);
        clearInterval(expInterval);
      } else {
        setAnimatedExp(Math.floor(expIncrement * expCount));
      }
    }, expDuration / expSteps);

    // クレジットのカウントアップアニメーション
    const creditsDuration = 1500;
    const creditsSteps = 30;
    const creditsIncrement = rewards.credits_gained / creditsSteps;
    let creditsCount = 0;

    const creditsInterval = setInterval(() => {
      creditsCount++;
      if (creditsCount >= creditsSteps) {
        setAnimatedCredits(rewards.credits_gained);
        clearInterval(creditsInterval);
      } else {
        setAnimatedCredits(Math.floor(creditsIncrement * creditsCount));
      }
    }, creditsDuration / creditsSteps);

    return () => {
      clearInterval(expInterval);
      clearInterval(creditsInterval);
    };
  }, [rewards, showContent]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="max-w-2xl w-full mx-4">
        {/* メインカード */}
        <div
          className={`rounded-lg border-4 p-8 transform transition-all duration-500 ${
            showContent ? "scale-100 opacity-100" : "scale-75 opacity-0"
          } ${
            winLoss === "WIN"
              ? "bg-gradient-to-br from-green-900/90 to-blue-900/90 border-green-500"
              : winLoss === "LOSE"
              ? "bg-gradient-to-br from-red-900/90 to-gray-900/90 border-red-500"
              : "bg-gradient-to-br from-yellow-900/90 to-gray-900/90 border-yellow-500"
          }`}
        >
          {/* 結果タイトル */}
          <div className="text-center mb-8">
            <div
              className={`inline-block px-8 py-4 rounded-lg text-5xl font-bold animate-pulse ${
                winLoss === "WIN"
                  ? "bg-green-500/30 text-green-300 border-2 border-green-400"
                  : winLoss === "LOSE"
                  ? "bg-red-500/30 text-red-300 border-2 border-red-400"
                  : "bg-yellow-500/30 text-yellow-300 border-2 border-yellow-400"
              }`}
            >
              {winLoss === "WIN" && "★ MISSION COMPLETE ★"}
              {winLoss === "LOSE" && "✕ MISSION FAILED ✕"}
              {winLoss === "DRAW" && "- DRAW -"}
            </div>

            {/* 装飾エフェクト */}
            {winLoss === "WIN" && (
              <div className="mt-4 text-6xl animate-bounce">🎉</div>
            )}
            {winLoss === "LOSE" && (
              <div className="mt-4 text-4xl text-red-400">⚠️</div>
            )}
          </div>

          {/* 報酬表示 */}
          {rewards && (
            <div className="space-y-4 mb-8">
              <h3 className="text-xl font-bold text-yellow-400 text-center border-b-2 border-yellow-500/50 pb-2">
                獲得報酬
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 経験値 */}
                <div className="bg-black/40 rounded-lg p-6 border-2 border-green-700">
                  <p className="text-sm text-gray-400 mb-2">経験値</p>
                  <p className="text-4xl font-bold text-green-400">
                    +{animatedExp}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    累積: {rewards.total_exp} EXP
                  </p>
                </div>

                {/* クレジット */}
                <div className="bg-black/40 rounded-lg p-6 border-2 border-yellow-700">
                  <p className="text-sm text-gray-400 mb-2">クレジット</p>
                  <p className="text-4xl font-bold text-yellow-400">
                    +{animatedCredits.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    所持金: {rewards.total_credits.toLocaleString()} CR
                  </p>
                </div>
              </div>

              {/* レベルアップ表示 */}
              {rewards.level_after > rewards.level_before && (
                <div className="bg-gradient-to-r from-yellow-500/20 to-orange-500/20 rounded-lg p-6 border-2 border-yellow-400 animate-pulse">
                  <p className="text-center text-2xl font-bold text-yellow-300">
                    🎉 LEVEL UP! 🎉
                  </p>
                  <p className="text-center text-xl text-yellow-400 mt-2">
                    Lv.{rewards.level_before} → Lv.{rewards.level_after}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 閉じるボタン */}
          <button
            onClick={onClose}
            className="w-full px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white font-bold rounded-lg transition-colors border border-gray-500"
          >
            CONTINUE
          </button>
        </div>
      </div>
    </div>
  );
}
