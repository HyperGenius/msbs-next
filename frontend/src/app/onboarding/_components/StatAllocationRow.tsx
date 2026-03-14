import type { StatKey } from "../_types";

interface StatAllocationRowProps {
  stat: StatKey;
  description: string;
  bonus: number;
  canDecrement: boolean;
  canIncrement: boolean;
  onDecrement: () => void;
  onIncrement: () => void;
}

export function StatAllocationRow({
  stat,
  description,
  bonus,
  canDecrement,
  canIncrement,
  onDecrement,
  onIncrement,
}: StatAllocationRowProps) {
  return (
    <div className="border border-[#00ff41]/20 bg-[#0a0a0a] p-3">
      <div className="flex items-center justify-between mb-1">
        <div>
          <span className="font-bold text-[#00ff41]">{stat}</span>
          <span className="text-xs text-[#00ff41]/50 ml-2">{description}</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onDecrement}
            disabled={!canDecrement}
            className="w-7 h-7 border border-[#00ff41]/40 text-[#00ff41] disabled:opacity-30 hover:bg-[#00ff41]/10 transition-colors"
          >
            −
          </button>
          <div className="text-center min-w-[3rem]">
            <span className="text-[#ffb000] text-sm"> +{bonus}</span>
          </div>
          <button
            type="button"
            onClick={onIncrement}
            disabled={!canIncrement}
            className="w-7 h-7 border border-[#00ff41]/40 text-[#00ff41] disabled:opacity-30 hover:bg-[#00ff41]/10 transition-colors"
          >
            ＋
          </button>
        </div>
      </div>
    </div>
  );
}
