"use client";

import React, { useState, useEffect } from "react";
import { BattleRewards, MobileSuit } from "@/types/battle";

interface BattleResultModalProps {
  winLoss: "WIN" | "LOSE" | "DRAW";
  rewards: BattleRewards | null;
  msSnapshot?: MobileSuit | null;
  kills?: number;
  onClose: () => void;
}

export default function BattleResultModal({
  winLoss,
  rewards,
  msSnapshot,
  kills,
  onClose,
}: BattleResultModalProps) {
  const [showContent, setShowContent] = useState(false);
  const [showRewards, setShowRewards] = useState(false);
  const [showLevelUp, setShowLevelUp] = useState(false);
  const [animatedExp, setAnimatedExp] = useState(0);
  const [animatedCredits, setAnimatedCredits] = useState(0);

  const isWin = winLoss === "WIN";
  const isLose = winLoss === "LOSE";

  useEffect(() => {
    // Step 1: 結果タイトル表示
    const timer1 = setTimeout(() => setShowContent(true), 300);
    // Step 2: 報酬表示（ステージ演出）
    const timer2 = setTimeout(() => setShowRewards(true), 900);
    // Step 3: レベルアップ演出（報酬表示後）
    const timer3 = setTimeout(() => {
      if (rewards && rewards.level_after > rewards.level_before) {
        setShowLevelUp(true);
      }
    }, 2400);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, [rewards]);

  useEffect(() => {
    if (!rewards || !showRewards) return;

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
  }, [rewards, showRewards]);

  // テーマカラー定義
  const theme = {
    border: isWin
      ? "border-blue-500"
      : isLose
      ? "border-red-600"
      : "border-yellow-500",
    bg: isWin
      ? "bg-gradient-to-br from-blue-900/90 to-slate-900/90"
      : isLose
      ? "bg-gradient-to-br from-red-900/90 to-gray-900/90"
      : "bg-gradient-to-br from-yellow-900/90 to-gray-900/90",
    resultBg: isWin
      ? "bg-blue-500/20 text-blue-200 border-2 border-blue-400"
      : isLose
      ? "bg-red-600/20 text-red-200 border-2 border-red-500"
      : "bg-yellow-500/20 text-yellow-200 border-2 border-yellow-400",
    accent: isWin ? "text-yellow-400" : isLose ? "text-red-400" : "text-yellow-400",
    statBorder: isWin ? "border-blue-700" : isLose ? "border-red-800" : "border-yellow-700",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm">
      {/* レベルアップエフェクト（オーバーレイ） */}
      {showLevelUp && (
        <div
          className="absolute inset-0 flex items-center justify-center z-50 pointer-events-none"
          style={{ animation: "levelUpFadeIn 0.5s ease-out forwards" }}
        >
          {/* パーティクル背景 */}
          <div className="absolute inset-0 overflow-hidden">
            {Array.from({ length: 20 }).map((_, i) => {
              const rx = Math.random();
              const ry = Math.random();
              return (
                <div
                  key={i}
                  className="absolute w-2 h-2 rounded-full bg-yellow-400 opacity-0"
                  style={{
                    left: `${Math.random() * 100}%`,
                    top: `${Math.random() * 100}%`,
                    animation: `particleFly ${0.8 + Math.random() * 1.2}s ease-out ${Math.random() * 0.5}s forwards`,
                    "--rx": String(rx),
                    "--ry": String(ry),
                  } as React.CSSProperties}
                />
              );
            })}
          </div>
          {/* LEVEL UP テキスト */}
          <div
            className="text-5xl font-bold text-yellow-400 z-10"
            style={{
              textShadow: "0 0 20px rgba(250, 204, 21, 0.9), 0 0 40px rgba(250, 204, 21, 0.6), 0 0 80px rgba(250, 204, 21, 0.3)",
              animation: "levelUpPulse 0.6s ease-out forwards",
            }}
          >
            LEVEL UP!!
          </div>
        </div>
      )}

      <div className="max-w-2xl w-full mx-4 relative">
        {/* メインカード */}
        <div
          className={`rounded-lg border-4 p-8 transform transition-all duration-500 ${
            showContent ? "scale-100 opacity-100" : "scale-75 opacity-0"
          } ${theme.bg} ${theme.border}`}
        >
          {/* 結果タイトル */}
          <div className="text-center mb-6">
            <div className={`inline-block px-8 py-4 rounded-lg text-5xl font-bold animate-pulse ${theme.resultBg}`}>
              {winLoss === "WIN" && "★ MISSION COMPLETE ★"}
              {winLoss === "LOSE" && "✕ MISSION FAILED ✕"}
              {winLoss === "DRAW" && "- DRAW -"}
            </div>

            {winLoss === "WIN" && (
              <div className="mt-4 text-6xl animate-bounce">🎉</div>
            )}
            {winLoss === "LOSE" && (
              <div className="mt-4 text-4xl text-red-400">⚠️</div>
            )}
          </div>

          {/* 機体スナップショット表示 */}
          {msSnapshot && (
            <div className={`mb-5 rounded-lg p-4 border ${theme.statBorder} bg-black/40`}>
              <h3 className={`text-sm font-bold mb-3 uppercase tracking-wider ${theme.accent}`}>
                出撃機体
              </h3>
              <div className="flex items-start gap-4">
                <div className="flex-1">
                  <p className="text-white font-bold text-lg">{msSnapshot.name}</p>
                  {msSnapshot.weapons && msSnapshot.weapons.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {msSnapshot.weapons.slice(0, 2).map((weapon, i) => (
                        <p key={i} className="text-xs text-gray-400">
                          <span className="text-gray-500">{i === 0 ? "メイン: " : "サブ: "}</span>
                          {weapon.name}
                          <span className="ml-2 text-gray-600">威力 {weapon.power}</span>
                        </p>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right text-xs text-gray-500 space-y-1">
                  <p>HP: <span className="text-white">{msSnapshot.max_hp}</span></p>
                  <p>装甲: <span className="text-white">{msSnapshot.armor}</span></p>
                  <p>機動: <span className="text-white">{msSnapshot.mobility?.toFixed(1)}</span></p>
                </div>
              </div>
            </div>
          )}

          {/* 戦果詳細（撃墜数） */}
          {(kills !== undefined && kills > 0) && (
            <div className={`mb-4 rounded-lg p-3 border ${theme.statBorder} bg-black/40 text-center`}>
              <p className="text-xs text-gray-400 mb-1">撃墜数</p>
              <p className={`text-3xl font-bold ${theme.accent}`}>{kills}</p>
            </div>
          )}

          {/* 報酬表示 */}
          {rewards && (
            <div
              className={`space-y-4 mb-8 transition-all duration-700 ${
                showRewards ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
            >
              <h3 className={`text-xl font-bold text-center border-b-2 pb-2 ${theme.accent} border-current/50`}>
                獲得報酬
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 経験値 */}
                <div className={`bg-black/40 rounded-lg p-6 border-2 ${theme.statBorder}`}>
                  <p className="text-sm text-gray-400 mb-2">経験値</p>
                  <p className={`text-4xl font-bold ${isWin ? "text-blue-300" : "text-gray-300"}`}>
                    +{animatedExp}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    累積: {rewards.total_exp} EXP
                  </p>
                </div>

                {/* クレジット */}
                <div className={`bg-black/40 rounded-lg p-6 border-2 ${theme.statBorder}`}>
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
                <div
                  className={`rounded-lg p-4 border-2 border-yellow-400 text-center transition-all duration-500 ${
                    showLevelUp
                      ? "bg-yellow-500/30 scale-105"
                      : "bg-yellow-500/10 scale-100"
                  }`}
                >
                  <p className="text-2xl font-bold text-yellow-300">
                    🎉 LEVEL UP! 🎉
                  </p>
                  <p className="text-xl text-yellow-400 mt-1">
                    Lv.{rewards.level_before} → Lv.{rewards.level_after}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 閉じるボタン */}
          <button
            onClick={onClose}
            className={`w-full px-6 py-3 font-bold rounded-lg transition-colors border ${
              isWin
                ? "bg-blue-800 hover:bg-blue-700 text-blue-100 border-blue-600"
                : isLose
                ? "bg-gray-700 hover:bg-gray-600 text-white border-gray-500"
                : "bg-gray-700 hover:bg-gray-600 text-white border-gray-500"
            }`}
          >
            CONTINUE
          </button>
        </div>
      </div>

      {/* CSS アニメーション定義 */}
      <style>{`
        @keyframes levelUpFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes levelUpPulse {
          0% { transform: scale(0.5); opacity: 0; }
          60% { transform: scale(1.3); opacity: 1; }
          100% { transform: scale(1.0); opacity: 1; }
        }
        @keyframes particleFly {
          0% { transform: translate(0, 0) scale(1); opacity: 1; }
          100% { transform: translate(
            calc((var(--rx, 0.5) - 0.5) * 400px),
            calc((var(--ry, 0.5) - 0.5) * 400px)
          ) scale(0); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
