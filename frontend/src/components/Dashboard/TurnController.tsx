/* frontend/src/components/Dashboard/TurnController.tsx */
import { SciFiPanel, SciFiButton } from "@/components/ui";

interface TurnControllerProps {
  currentTimestamp: number;
  maxTimestamp: number;
  onTimestampChange: (timestamp: number) => void;
}

/**
 * バトルビューアのタイムスタンプ操作コントローラ（スライダー・PREV/NEXT ボタン）。
 */
export default function TurnController({
  currentTimestamp,
  maxTimestamp,
  onTimestampChange,
}: TurnControllerProps) {
  const step = 0.1;

  const handlePrev = () => {
    const next = Math.round(Math.max(0, currentTimestamp - step) * 10) / 10;
    onTimestampChange(next);
  };

  const handleNext = () => {
    const next = Math.round(Math.min(maxTimestamp, currentTimestamp + step) * 10) / 10;
    onTimestampChange(next);
  };

  return (
    <SciFiPanel variant="accent" className="mt-2">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4 p-3 sm:p-4">
        {/* モバイル用ボタン（並列表示） */}
        <div className="flex gap-2 sm:hidden">
          <SciFiButton
            onClick={handlePrev}
            disabled={currentTimestamp <= 0}
            variant="accent"
            size="sm"
            className="flex-1"
          >
            &lt; PREV
          </SciFiButton>
          <SciFiButton
            onClick={handleNext}
            disabled={currentTimestamp >= maxTimestamp}
            variant="accent"
            size="sm"
            className="flex-1"
          >
            NEXT &gt;
          </SciFiButton>
        </div>

        {/* デスクトップ用 PREV ボタン */}
        <SciFiButton
          onClick={handlePrev}
          disabled={currentTimestamp <= 0}
          variant="accent"
          size="sm"
          className="hidden sm:block"
        >
          &lt; PREV
        </SciFiButton>

        {/* スライダー */}
        <div className="flex-grow flex flex-col px-2 sm:px-4">
          <input
            type="range"
            min="0"
            max={maxTimestamp}
            step={step}
            value={currentTimestamp}
            onChange={(e) => onTimestampChange(Math.round(Number(e.target.value) * 10) / 10)}
            className="w-full h-2 bg-[#0a0a0a] rounded-lg appearance-none cursor-pointer accent-[#00f0ff] touch-manipulation"
          />
          <div className="flex justify-between text-[10px] sm:text-xs mt-1 text-[#00f0ff]/60">
            <span>Start</span>
            <span>
              Time: {currentTimestamp.toFixed(1)}s / {maxTimestamp.toFixed(1)}s
            </span>
            <span>End</span>
          </div>
        </div>

        {/* デスクトップ用 NEXT ボタン */}
        <SciFiButton
          onClick={handleNext}
          disabled={currentTimestamp >= maxTimestamp}
          variant="accent"
          size="sm"
          className="hidden sm:block"
        >
          NEXT &gt;
        </SciFiButton>
      </div>
    </SciFiPanel>
  );
}
