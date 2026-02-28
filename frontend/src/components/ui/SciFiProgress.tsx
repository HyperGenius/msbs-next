interface SciFiProgressProps {
  /** Progress value 0–100 */
  value: number;
  /** Whether this change will trigger a rank-up (visual emphasis) */
  isRankUp?: boolean;
  className?: string;
}

/**
 * SciFiデザインシステムに準拠した進捗バーコンポーネント。
 * ランク内の進捗率を 0〜100% で表示し、ランクアップ時は視覚的に強調します。
 */
export default function SciFiProgress({
  value,
  isRankUp = false,
  className = "",
}: SciFiProgressProps) {
  const clampedValue = Math.min(100, Math.max(0, value));

  const barColor = isRankUp
    ? "bg-[#00f0ff] shadow-[0_0_8px_#00f0ff]"
    : "bg-[#00ff41]";

  const trackColor = isRankUp
    ? "border-[#00f0ff]/40"
    : "border-[#00ff41]/30";

  return (
    <div className={`w-full ${className}`}>
      <div
        className={`relative h-2 bg-[#0a0a0a] rounded-full border ${trackColor} overflow-hidden`}
        role="progressbar"
        aria-valuenow={clampedValue}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full rounded-full transition-all duration-300 ${barColor}`}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      <p
        className={`text-[10px] text-[#00f0ff] mt-0.5 font-bold uppercase tracking-widest animate-pulse ${isRankUp ? "visible" : "invisible"}`}
      >
        RANK UP!
      </p>
    </div>
  );
}
