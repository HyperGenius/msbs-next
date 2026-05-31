"use client";

interface StatusPointGaugeProps {
  /** 保存前の元のポイント総量 */
  total: number;
  /** 保留後の残ポイント（total - 保留分の合計） */
  remaining: number;
}

/** 残量割合に応じたゲージバーの色を返す */
function getGaugeColor(remaining: number, total: number): string {
  if (total === 0) return "#6b7280";
  const ratio = remaining / total;
  if (ratio > 0.66) return "#00ff41";
  if (ratio > 0.33) return "#ffb000";
  if (remaining > 0) return "#ff8800";
  return "#ff4444";
}

/**
 * ステータスポイントの残量をバッテリー型ゲージで可視化するコンポーネント。
 * 残量に応じて Green → Amber → Orange → Red に変色し、
 * 0 になると警告パルスアニメーションを表示する。
 */
export default function StatusPointGauge({ total, remaining }: StatusPointGaugeProps) {
  const gaugeColor = getGaugeColor(remaining, total);
  const gaugePct = total > 0 ? Math.max(0, Math.min((remaining / total) * 100, 100)) : 0;
  const isEmpty = remaining <= 0;

  return (
    <div className="border border-[#ffb000]/30 bg-[#ffb000]/5 p-3 flex flex-col gap-2">
      {/* ラベル */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold tracking-widest text-[#ffb000] uppercase">
          Status Points
        </span>
        {/* 残量数値: 0 のときは警告パルス */}
        <span
          className={`text-lg font-bold tabular-nums ${isEmpty ? "animate-pulse" : ""}`}
          style={{ color: gaugeColor }}
        >
          {remaining}
          <span className="text-xs text-gray-500 font-normal"> / {total} pt</span>
        </span>
      </div>
    </div>
  );
}
