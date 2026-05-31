"use client";

import { StatKey } from "./StatusRadarChart";

/** ステータス表示名・略称・ゲーム効果説明 */
export const STATUS_LABELS: Record<StatKey, { label: string; abbr: string; desc: string }> = {
  // TODO: 各ステータスの説明文を充実させる（エンジンでの補正値ではなくユーザーの直感的な理解を優先）
  sht:   { label: "射撃精度", abbr: "SHT", desc: "" },
  mel:   { label: "格闘技巧", abbr: "MEL", desc: "" },
  intel: { label: "直感",    abbr: "INT", desc: "" },
  ref:   { label: "反応",    abbr: "REF", desc: "" },
  tou:   { label: "耐久",    abbr: "TOU", desc: "" },
  luk:   { label: "幸運",    abbr: "LUK", desc: "" },
};

/** ランク色（S〜D の5段階） */
export const STAT_RANK_COLORS: Record<string, string> = {
  S: "#ff4444",
  A: "#ffb000",
  B: "#00ff41",
  C: "#00f0ff",
  D: "#6b7280",
};

/** ステータス値からランクを算出する（S/A/B/C/D の5段階） */
export function getStatRank(value: number): string {
  if (value >= 20) return "S";
  if (value >= 15) return "A";
  if (value >= 10) return "B";
  if (value >= 5) return "C";
  return "D";
}

/** プログレスバーの最大スケール */
const STAT_MAX = 25;

interface StatusStatCardProps {
  stat: StatKey;
  /** パイロットの現在値 */
  currentValue: number;
  /** 保留中の加算分（未保存） */
  pending: number;
  /** 保留後の残ポイント */
  remainingPoints: number;
  onIncrease: () => void;
  onDecrease: () => void;
}

/**
 * 個々のステータスを表示・操作するカードコンポーネント。
 * 説明文・プログレスバー・現在→保留後の変化を表示する。
 */
export default function StatusStatCard({
  stat,
  currentValue,
  pending,
  remainingPoints,
  onIncrease,
  onDecrease,
}: StatusStatCardProps) {
  const info = STATUS_LABELS[stat];
  const afterValue = currentValue + pending;
  const currentRank = getStatRank(currentValue);
  const afterRank = getStatRank(afterValue);
  const afterColor = STAT_RANK_COLORS[afterRank];

  /** プログレスバーの現在値幅（%） */
  const currentPct = Math.min((currentValue / STAT_MAX) * 100, 100);
  /** 保留分の追加幅（%） */
  const pendingPct = Math.min((pending / STAT_MAX) * 100, 100 - currentPct);

  return (
    <div className="border border-[#ffb000]/30 bg-[#ffb000]/5 p-3 flex flex-col gap-2">
      {/* ヘッダー: 略称・日本語名・説明文 */}
      <div>
        <p className="text-base font-bold text-[#ffb000] uppercase leading-tight">
          {info.abbr}{" "}
          <span className="text-gray-300 text-xs normal-case font-normal">/ {info.label}</span>
        </p>
        <p className="text-[10px] text-gray-500 leading-snug mt-0.5">{info.desc}</p>
      </div>

      {/* 値の変化表示: 現在 → +N → 保留後 */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-400">
          <span className={`font-bold`} style={{ color: STAT_RANK_COLORS[currentRank] }}>
            {currentRank}({currentValue})
          </span>
        </span>
        {pending > 0 && (
          <>
            <span className="text-[#00f0ff] font-bold">→ +{pending}</span>
            <span>
              <span className="font-bold" style={{ color: afterColor }}>
                {afterRank}({afterValue})
              </span>
            </span>
          </>
        )}
      </div>

      {/* 増減ボタン */}
      <div className="flex gap-2">
        <button
          onClick={onDecrease}
          disabled={pending <= 0}
          className="flex-1 py-1.5 border border-[#ffb000]/50 bg-[#ffb000]/5 text-[#ffb000] text-sm font-bold
            hover:border-[#ffb000] hover:bg-[#ffb000]/15
            disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-[#ffb000]/5 disabled:hover:border-[#ffb000]/50
            transition-colors"
        >
          −
        </button>
        <button
          onClick={onIncrease}
          disabled={remainingPoints <= 0}
          className="flex-1 py-1.5 border border-[#00ff41]/50 bg-[#00ff41]/5 text-[#00ff41] text-sm font-bold
            hover:border-[#00ff41] hover:bg-[#00ff41]/15
            disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-[#00ff41]/5 disabled:hover:border-[#00ff41]/50
            transition-colors"
        >
          ＋
        </button>
      </div>
    </div>
  );
}
