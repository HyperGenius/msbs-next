import type { Background } from "../_types";

interface BackgroundCardProps {
  background: Background;
  isSelected: boolean;
  onSelect: (bg: Background) => void;
}

export function BackgroundCard({ background, isSelected, onSelect }: BackgroundCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(background)}
      className={`w-full p-4 border-2 text-left transition-all duration-200 font-mono
        ${isSelected
          ? "border-[#00ff41] bg-[#00ff41]/10 text-[#00ff41]"
          : "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]/60 hover:border-[#00ff41]/60 hover:text-[#00ff41]/80"
        }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            {isSelected && <span className="text-[#00ff41] text-xs">▶</span>}
            <span className="font-bold underline">{background.name}</span>
          </div>
          <p className="text-sm opacity-70 leading-relaxed">{background.description}</p>
        </div>
      </div>
    </button>
  );
}
