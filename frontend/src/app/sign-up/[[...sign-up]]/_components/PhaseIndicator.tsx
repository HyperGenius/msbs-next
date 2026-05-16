"use client";

import { PHASE_LABELS, WizardPhase } from "../_constants";

/**
 * ウィザードの進捗を視覚的に示すフェーズインジケーター
 * 現在のフェーズに応じてバーをハイライト表示する
 */
export function PhaseIndicator({
  currentPhase,
  variant,
}: {
  currentPhase: WizardPhase;
  variant: "primary" | "secondary" | "accent";
}) {
  /** バリアントごとのバー色クラス */
  const barColor: Record<string, string> = {
    primary: "bg-[#00ff41]",
    secondary: "bg-[#ffb000]",
    accent: "bg-[#00f0ff]",
  };
  /** バリアントごとのテキスト色クラス */
  const textColor: Record<string, string> = {
    primary: "text-[#00ff41]",
    secondary: "text-[#ffb000]",
    accent: "text-[#00f0ff]",
  };
  return (
    <div className="text-center">
      <div className="flex justify-center gap-1.5 mt-3">
        {[1, 2, 3, 4, 5].map((n) => (
          <div
            key={n}
            className={`h-1 w-12 transition-all duration-300 ${
              currentPhase >= n
                ? barColor[variant]
                : `${barColor[variant]} opacity-20`
            }`}
          />
        ))}
      </div>
      <p
        className={`${textColor[variant]} opacity-40 text-xs mt-2 font-mono`}
      >
        PHASE {currentPhase} / 5 — {PHASE_LABELS[currentPhase - 1]}
      </p>
    </div>
  );
}
