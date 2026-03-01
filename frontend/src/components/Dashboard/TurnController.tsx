/* frontend/src/components/Dashboard/TurnController.tsx */
import { SciFiPanel, SciFiButton } from "@/components/ui";

interface TurnControllerProps {
  currentTurn: number;
  maxTurn: number;
  onTurnChange: (turn: number) => void;
}

/**
 * バトルビューアのターン操作コントローラ（スライダー・PREV/NEXT ボタン）。
 */
export default function TurnController({
  currentTurn,
  maxTurn,
  onTurnChange,
}: TurnControllerProps) {
  return (
    <SciFiPanel variant="accent" className="mt-2">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4 p-3 sm:p-4">
        {/* モバイル用ボタン（並列表示） */}
        <div className="flex gap-2 sm:hidden">
          <SciFiButton
            onClick={() => onTurnChange(Math.max(0, currentTurn - 1))}
            disabled={currentTurn <= 0}
            variant="accent"
            size="sm"
            className="flex-1"
          >
            &lt; PREV
          </SciFiButton>
          <SciFiButton
            onClick={() => onTurnChange(Math.min(maxTurn, currentTurn + 1))}
            disabled={currentTurn >= maxTurn}
            variant="accent"
            size="sm"
            className="flex-1"
          >
            NEXT &gt;
          </SciFiButton>
        </div>

        {/* デスクトップ用 PREV ボタン */}
        <SciFiButton
          onClick={() => onTurnChange(Math.max(0, currentTurn - 1))}
          disabled={currentTurn <= 0}
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
            max={maxTurn}
            value={currentTurn}
            onChange={(e) => onTurnChange(Number(e.target.value))}
            className="w-full h-2 bg-[#0a0a0a] rounded-lg appearance-none cursor-pointer accent-[#00f0ff] touch-manipulation"
          />
          <div className="flex justify-between text-[10px] sm:text-xs mt-1 text-[#00f0ff]/60">
            <span>Start</span>
            <span>
              Turn: {currentTurn} / {maxTurn}
            </span>
            <span>End</span>
          </div>
        </div>

        {/* デスクトップ用 NEXT ボタン */}
        <SciFiButton
          onClick={() => onTurnChange(Math.min(maxTurn, currentTurn + 1))}
          disabled={currentTurn >= maxTurn}
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
