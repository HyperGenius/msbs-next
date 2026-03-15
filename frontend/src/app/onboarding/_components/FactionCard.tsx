import type { Faction } from "../_types";

const FACTION_STYLES: Record<
  Faction,
  { selected: string; unselected: string; badge: string }
> = {
  FEDERATION: {
    selected: "border-[#00f0ff] bg-[#00f0ff]/10 text-[#00f0ff]",
    unselected:
      "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]/60 hover:border-[#00f0ff]/60 hover:text-[#00f0ff]/80",
    badge: "text-[#00f0ff]",
  },
  ZEON: {
    selected: "border-[#ff4400] bg-[#ff4400]/10 text-[#ff4400]",
    unselected:
      "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]/60 hover:border-[#ff4400]/60 hover:text-[#ff4400]/80",
    badge: "text-[#ff4400]",
  },
};

interface FactionCardProps {
  faction: Faction;
  label: string;
  subLabel: string;
  mobilesuit: string;
  isSelected: boolean;
  onSelect: (faction: Faction) => void;
}

export function FactionCard({
  faction,
  label,
  subLabel,
  mobilesuit,
  isSelected,
  onSelect,
}: FactionCardProps) {
  const styles = FACTION_STYLES[faction];
  return (
    <button
      type="button"
      onClick={() => onSelect(faction)}
      className={`relative p-4 border-2 text-left transition-all duration-200 font-mono ${
        isSelected ? styles.selected : styles.unselected
      }`}
    >
      {isSelected && (
        <span className={`absolute top-2 right-2 text-xs ${styles.badge}`}>▶ SELECTED</span>
      )}
      <div className="text-lg font-bold mb-1">{label}</div>
      <div className="text-xs opacity-80">{subLabel}</div>
      <div className="mt-2 text-xs opacity-60">練習機: {mobilesuit}</div>
    </button>
  );
}

