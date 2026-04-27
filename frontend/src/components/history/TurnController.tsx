/* frontend/src/components/history/TurnController.tsx */
"use client";

interface TurnControllerProps {
  currentTimestamp: number;
  maxTimestamp: number;
  onTimestampChange: (timestamp: number) => void;
}

export default function TurnController({ currentTimestamp, maxTimestamp, onTimestampChange }: TurnControllerProps) {
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
    <div className="mt-2 p-3 bg-gray-900 border border-green-800 rounded">
      <div className="flex items-center gap-3">
        <button
          onClick={handlePrev}
          disabled={currentTimestamp <= 0}
          className="px-3 py-1 bg-green-900 hover:bg-green-800 disabled:opacity-30 rounded text-sm font-bold transition-colors"
        >
          &lt; PREV
        </button>
        <div className="flex-grow flex flex-col">
          <input
            type="range"
            min="0"
            max={maxTimestamp}
            step={step}
            value={currentTimestamp}
            onChange={(e) => onTimestampChange(Math.round(Number(e.target.value) * 10) / 10)}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
          <div className="flex justify-between text-xs mt-1 text-green-600/60">
            <span>Start</span>
            <span>Time: {currentTimestamp.toFixed(1)}s / {maxTimestamp.toFixed(1)}s</span>
            <span>End</span>
          </div>
        </div>
        <button
          onClick={handleNext}
          disabled={currentTimestamp >= maxTimestamp}
          className="px-3 py-1 bg-green-900 hover:bg-green-800 disabled:opacity-30 rounded text-sm font-bold transition-colors"
        >
          NEXT &gt;
        </button>
      </div>
    </div>
  );
}
