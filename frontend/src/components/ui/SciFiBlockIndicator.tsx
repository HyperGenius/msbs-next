const TOTAL_BLOCKS = 12;

interface SciFiBlockIndicatorProps {
  /** Current stat value */
  currentValue: number;
  /** Stat cap (maximum possible value) */
  cap: number;
  /** Number of pending upgrade steps */
  pendingSteps: number;
  /** Value increment per upgrade step */
  increment: number;
  className?: string;
}

/**
 * ブロック状の強化インジケーター。
 * 🟩: 現在の強化済みブロック
 * 🟨: 今回追加予定の強化ブロック
 * ⬛: 残りの強化可能ブロック
 */
export default function SciFiBlockIndicator({
  currentValue,
  cap,
  pendingSteps,
  increment,
  className = "",
}: SciFiBlockIndicatorProps) {
  if (cap <= 0) {
    return <div className={`flex gap-0.5 ${className}`} />;
  }

  const afterValue = Math.min(currentValue + pendingSteps * increment, cap);
  const currentBlocks = Math.round((currentValue / cap) * TOTAL_BLOCKS);
  const afterBlocks = Math.round((afterValue / cap) * TOTAL_BLOCKS);
  const pendingBlocks = afterBlocks - currentBlocks;
  const emptyBlocks = TOTAL_BLOCKS - afterBlocks;

  return (
    <div className={`flex gap-0.5 ${className}`} role="meter" aria-valuenow={currentBlocks} aria-valuemax={TOTAL_BLOCKS}>
      {Array.from({ length: currentBlocks }).map((_, i) => (
        <span
          key={`current-${i}`}
          className="w-3 h-5 bg-[#00ff41] border border-[#00ff41]/60 inline-block"
          aria-hidden="true"
        />
      ))}
      {Array.from({ length: pendingBlocks }).map((_, i) => (
        <span
          key={`pending-${i}`}
          className="w-3 h-5 bg-[#ffb000] border border-[#ffb000]/60 inline-block"
          aria-hidden="true"
        />
      ))}
      {Array.from({ length: emptyBlocks }).map((_, i) => (
        <span
          key={`empty-${i}`}
          className="w-3 h-5 bg-[#1a1a1a] border border-[#00ff41]/20 inline-block"
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
