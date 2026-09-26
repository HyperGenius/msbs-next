"use client";

import React, { useState, useEffect } from "react";
import { BattleRewards, LootItem, MobileSuit } from "@/types/battle";
import MobileSuitRankBadges from "./MobileSuitRankBadges";
import LootList from "@/components/loot/LootList";
import { getWeaponPowerRank, getRankColor } from "@/utils/rankUtils";

type WinLoss = "WIN" | "LOSE" | "DRAW";

interface BattleResultModalProps {
  winLoss: WinLoss;
  rewards: BattleRewards | null;
  msSnapshot?: MobileSuit | null;
  kills?: number;
  /** 戦利品。空配列はドロップなし、null・未指定は導入前のバトルで、欄を出さない */
  loot?: LootItem[] | null;
  onClose: () => void;
  /** 指定したときだけ「リプレイを見る」ボタンを表示する */
  onOpenReplay?: () => void;
  /** false なら段階表示とカウントアップを省き、最終状態をすぐに表示する */
  animate?: boolean;
}

const CONTENT_DELAY_MS = 300;
const REWARDS_DELAY_MS = 900;
const COUNT_UP_MS = 1500;
const COUNT_UP_STEPS = 30;
// 戦利品は報酬のカウントアップが終わってから出す。
const LOOT_DELAY_MS = REWARDS_DELAY_MS + COUNT_UP_MS;
// 新規入手の演出とレベルアップ演出が重ならないよう、その分だけ遅らせる。
const NEW_LOOT_EFFECT_MS = 1000;

const THEMES: Record<
  WinLoss,
  {
    title: string;
    subtitle: string;
    color: string;
    text: string;
    border: string;
    button: string;
    outline: string;
  }
> = {
  WIN: {
    title: "MISSION COMPLETE",
    subtitle: "勝利",
    color: "#00ff41",
    text: "text-[#00ff41]",
    border: "border-[#00ff41] sf-border-glow-green",
    button: "bg-[#00ff41] text-black border-[#00ff41] hover:bg-[#00cc33]",
    outline: "border-[#00ff41]/60 text-[#00ff41] hover:bg-[#00ff41]/10",
  },
  LOSE: {
    title: "MISSION FAILED",
    subtitle: "敗北",
    color: "#ffb000",
    text: "text-[#ffb000]",
    border: "border-[#ffb000] sf-border-glow-amber",
    button: "bg-[#ffb000] text-black border-[#ffb000] hover:bg-[#cc8800]",
    outline: "border-[#ffb000]/60 text-[#ffb000] hover:bg-[#ffb000]/10",
  },
  DRAW: {
    title: "DRAW",
    subtitle: "引き分け",
    color: "#00f0ff",
    text: "text-[#00f0ff]",
    border: "border-[#00f0ff] sf-border-glow-cyan",
    button: "bg-[#00f0ff] text-black border-[#00f0ff] hover:bg-[#00b8cc]",
    outline: "border-[#00f0ff]/60 text-[#00f0ff] hover:bg-[#00f0ff]/10",
  },
};

const STAT_GRID_COLS: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-3",
};

// 描画のたびに乱数を使うと、再描画やストーリーごとに見た目が変わるため、配置を固定する。
const LEVEL_UP_PARTICLES = Array.from({ length: 20 }, (_, i) => {
  const angle = i * 2.39996; // 黄金角（rad）で円周上に散らす
  const radius = 0.15 + (i % 5) * 0.08;
  return {
    left: 50 + Math.cos(angle) * radius * 100,
    top: 50 + Math.sin(angle) * radius * 100,
    rx: 0.5 + Math.cos(angle) / 2,
    ry: 0.5 + Math.sin(angle) / 2,
    duration: 0.8 + (i % 4) * 0.3,
    delay: (i % 5) * 0.1,
  };
});

/** start が true になってから、0 から target まで数値をカウントアップする */
function useCountUp(target: number, start: boolean): number {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!start) return;
    let step = 0;
    const interval = setInterval(() => {
      step++;
      if (step >= COUNT_UP_STEPS) {
        setValue(target);
        clearInterval(interval);
      } else {
        setValue(Math.floor((target / COUNT_UP_STEPS) * step));
      }
    }, COUNT_UP_MS / COUNT_UP_STEPS);
    return () => clearInterval(interval);
  }, [target, start]);
  return value;
}

/** セクションの見出し（ホーム画面の「// NEXT BATTLE」と同じ形式） */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="text-[10px] tracking-widest text-gray-500">
        {"// "}
        {children}
      </span>
      <div className="flex-1 h-px bg-gray-700/60" />
    </div>
  );
}

/** 撃墜数・経験値・クレジットの1マス */
function StatCell({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className: string;
}) {
  return (
    <div className="bg-black/40 border border-gray-700/70 px-2 py-2 text-center min-w-0">
      <p className="text-[10px] tracking-widest text-gray-500">{label}</p>
      <p className={`text-xl sm:text-2xl font-bold truncate ${className}`}>
        {value}
      </p>
    </div>
  );
}

/**
 * BattleResultModal
 * バトル終了時のリザルト画面。
 * 結果タイトル → 報酬（カウントアップ）→ 戦利品 → レベルアップの順に段階表示する。
 * 本文だけをスクロールさせ、CONTINUE ボタンは常に画面内に置く。
 */
export default function BattleResultModal({
  winLoss,
  rewards,
  msSnapshot,
  kills,
  loot,
  onClose,
  onOpenReplay,
  animate = true,
}: BattleResultModalProps) {
  const [contentShown, setContentShown] = useState(false);
  const [rewardsShown, setRewardsShown] = useState(false);
  const [lootShown, setLootShown] = useState(false);
  const [levelUpShown, setLevelUpShown] = useState(false);

  const theme = THEMES[winLoss];
  const isLevelUp = !!rewards && rewards.level_after > rewards.level_before;
  const hasNewLoot = !!loot?.some((item) => item.is_new);

  useEffect(() => {
    if (!animate) return;
    const levelUpDelay = LOOT_DELAY_MS + (hasNewLoot ? NEW_LOOT_EFFECT_MS : 0);
    const timers = [
      setTimeout(() => setContentShown(true), CONTENT_DELAY_MS),
      setTimeout(() => setRewardsShown(true), REWARDS_DELAY_MS),
      setTimeout(() => setLootShown(true), LOOT_DELAY_MS),
      setTimeout(() => setLevelUpShown(isLevelUp), levelUpDelay),
    ];
    return () => timers.forEach(clearTimeout);
  }, [animate, hasNewLoot, isLevelUp]);

  const showContent = !animate || contentShown;
  const showRewards = !animate || rewardsShown;
  const showLoot = !animate || lootShown;

  const animatedExp = useCountUp(
    rewards?.exp_gained ?? 0,
    animate && rewardsShown,
  );
  const animatedCredits = useCountUp(
    rewards?.credits_gained ?? 0,
    animate && rewardsShown,
  );
  const exp = animate ? animatedExp : (rewards?.exp_gained ?? 0);
  const credits = animate ? animatedCredits : (rewards?.credits_gained ?? 0);

  const weapons = msSnapshot?.weapons?.slice(0, 2) ?? [];
  const statCount = (kills !== undefined ? 1 : 0) + (rewards ? 2 : 0);
  const hasStats = statCount > 0;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 font-mono"
      role="dialog"
      aria-modal="true"
      aria-labelledby="battle-result-title"
    >
      {/* レベルアップ演出（一定時間で消えるオーバーレイ） */}
      {levelUpShown && (
        <div
          className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none"
          style={{ animation: "levelUpOverlay 2s ease-out forwards" }}
          aria-hidden="true"
        >
          <div className="absolute inset-0 overflow-hidden">
            {LEVEL_UP_PARTICLES.map((p, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full bg-[#ffb000] opacity-0"
                style={
                  {
                    left: `${p.left}%`,
                    top: `${p.top}%`,
                    animation: `particleFly ${p.duration}s ease-out ${p.delay}s forwards`,
                    "--rx": String(p.rx),
                    "--ry": String(p.ry),
                  } as React.CSSProperties
                }
              />
            ))}
          </div>
          <div
            className="text-4xl sm:text-5xl font-bold text-[#ffb000]"
            style={{
              textShadow:
                "0 0 20px rgba(255, 176, 0, 0.9), 0 0 40px rgba(255, 176, 0, 0.5)",
              animation: "levelUpPulse 0.6s ease-out forwards",
            }}
          >
            LEVEL UP
          </div>
        </div>
      )}

      <div
        className={`relative w-full max-w-lg max-h-[calc(100dvh-2rem)] flex flex-col bg-[#0a0a0a]/95 border-2 sf-chiseled transform transition-all duration-500 ${
          theme.border
        } ${showContent ? "scale-100 opacity-100" : "scale-90 opacity-0"}`}
      >
        {/* 結果タイトル */}
        <header className="flex-none px-4 pt-4 pb-3 text-center border-b border-gray-800">
          <p className="text-[10px] tracking-[0.3em] text-gray-500">
            {"// BATTLE RESULT"}
          </p>
          <h2
            id="battle-result-title"
            className={`mt-1 text-2xl sm:text-3xl font-bold tracking-widest ${theme.text}`}
            style={{ textShadow: `0 0 12px ${theme.color}80` }}
          >
            {theme.title}
          </h2>
          <p className={`text-xs tracking-widest opacity-70 ${theme.text}`}>
            {theme.subtitle}
          </p>
        </header>

        {/* 本文（ここだけスクロールする） */}
        <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-4">
          {msSnapshot && (
            <section>
              <SectionLabel>出撃機体</SectionLabel>
              <p
                className="text-white font-bold text-base truncate"
                title={msSnapshot.name}
              >
                {msSnapshot.name}
              </p>
              <MobileSuitRankBadges
                mobileSuit={msSnapshot}
                className="text-xs sm:text-sm"
              />
              {weapons.length > 0 && (
                <div className="mt-1 space-y-0.5">
                  {weapons.map((weapon, i) => {
                    const powerRank = getWeaponPowerRank(weapon);
                    return (
                      <p
                        key={i}
                        className="flex items-center gap-2 text-xs text-gray-400 min-w-0"
                      >
                        <span className="shrink-0 text-gray-500">
                          {i === 0 ? "メイン" : "サブ"}
                        </span>
                        <span className="truncate" title={weapon.name}>
                          {weapon.name}
                        </span>
                        <span
                          className={`shrink-0 font-bold ${getRankColor(powerRank)}`}
                        >
                          威力 {powerRank}
                        </span>
                      </p>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          {hasStats && (
            <section
              className={`transition-all duration-700 ${
                showRewards
                  ? "opacity-100 translate-y-0"
                  : "opacity-0 translate-y-4"
              }`}
            >
              <SectionLabel>獲得報酬</SectionLabel>
              <div className={`grid gap-2 ${STAT_GRID_COLS[statCount]}`}>
                {kills !== undefined && (
                  <StatCell
                    label="撃墜"
                    value={String(kills)}
                    className={kills > 0 ? theme.text : "text-gray-500"}
                  />
                )}
                {rewards && (
                  <>
                    <StatCell
                      label="EXP"
                      value={`+${exp.toLocaleString()}`}
                      className="text-[#00ff41]"
                    />
                    <StatCell
                      label="CREDITS"
                      value={`+${credits.toLocaleString()}`}
                      className="text-[#ffb000]"
                    />
                  </>
                )}
              </div>

              {isLevelUp && rewards && (
                <div
                  className={`mt-2 flex items-center justify-between border px-3 py-2 transition-colors duration-500 ${
                    levelUpShown || !animate
                      ? "border-[#ffb000] bg-[#ffb000]/20"
                      : "border-[#ffb000]/40 bg-[#ffb000]/5"
                  }`}
                >
                  <span className="text-sm font-bold tracking-widest text-[#ffb000]">
                    LEVEL UP
                  </span>
                  <span className="text-sm font-bold text-[#ffb000]">
                    Lv.{rewards.level_before} → Lv.{rewards.level_after}
                  </span>
                </div>
              )}
            </section>
          )}

          {loot != null && (
            <section
              className={`transition-all duration-500 ${
                showLoot
                  ? "opacity-100 translate-y-0"
                  : "opacity-0 translate-y-4"
              }`}
            >
              <SectionLabel>戦利品</SectionLabel>
              <LootList loot={loot} animate={animate && lootShown} />
            </section>
          )}
        </div>

        {/* 操作ボタン（常に表示） */}
        <footer className="flex-none flex gap-2 p-3 border-t border-gray-800">
          {onOpenReplay && (
            <button
              type="button"
              onClick={onOpenReplay}
              className={`flex-1 px-3 py-3 text-sm font-bold border-2 bg-transparent transition-colors ${theme.outline}`}
            >
              リプレイを見る
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className={`flex-1 px-3 py-3 text-sm font-bold tracking-widest border-2 transition-colors ${theme.button}`}
          >
            CONTINUE
          </button>
        </footer>
      </div>

      <style>{`
        @keyframes levelUpOverlay {
          0% { opacity: 0; }
          15% { opacity: 1; }
          75% { opacity: 1; }
          100% { opacity: 0; }
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
