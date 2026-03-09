/* frontend/src/components/history/TurnController.tsx */
"use client";

interface TurnControllerProps {
  currentTurn: number;
  maxTurn: number;
  onTurnChange: (turn: number) => void;
}

export default function TurnController({ currentTurn, maxTurn, onTurnChange }: TurnControllerProps) {
  return (
    <div className="mt-2 p-3 bg-gray-900 border border-green-800 rounded">
      <div className="flex items-center gap-3">
        <button
          onClick={() => onTurnChange(Math.max(0, currentTurn - 1))}
          disabled={currentTurn <= 0}
          className="px-3 py-1 bg-green-900 hover:bg-green-800 disabled:opacity-30 rounded text-sm font-bold transition-colors"
        >
          &lt; PREV
        </button>
        <div className="flex-grow flex flex-col">
          <input
            type="range"
            min="0"
            max={maxTurn}
            value={currentTurn}
            onChange={(e) => onTurnChange(Number(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
          <div className="flex justify-between text-xs mt-1 text-green-600/60">
            <span>Start</span>
            <span>Turn: {currentTurn} / {maxTurn}</span>
            <span>End</span>
          </div>
        </div>
        <button
          onClick={() => onTurnChange(Math.min(maxTurn, currentTurn + 1))}
          disabled={currentTurn >= maxTurn}
          className="px-3 py-1 bg-green-900 hover:bg-green-800 disabled:opacity-30 rounded text-sm font-bold transition-colors"
        >
          NEXT &gt;
        </button>
      </div>
    </div>
  );
}
