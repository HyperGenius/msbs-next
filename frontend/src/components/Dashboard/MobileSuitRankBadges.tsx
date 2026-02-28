import { MobileSuit } from "@/types/battle";
import { getRankColor } from "@/utils/rankUtils";

const RANK_ITEMS: { label: string; key: keyof Pick<MobileSuit, "hp_rank" | "armor_rank" | "mobility_rank"> }[] = [
  { label: "HP", key: "hp_rank" },
  { label: "装甲", key: "armor_rank" },
  { label: "機動", key: "mobility_rank" },
];

interface MobileSuitRankBadgesProps {
  mobileSuit: MobileSuit;
}

export default function MobileSuitRankBadges({ mobileSuit }: MobileSuitRankBadgesProps) {
  return (
    <div className="flex gap-3 text-sm">
      {RANK_ITEMS.map(({ label, key }) => {
        const rank = mobileSuit[key] ?? "C";
        return (
          <span key={key} className="flex items-center gap-1 text-gray-400">
            {label}:
            <span className={`font-bold ${getRankColor(rank)}`}>{rank}</span>
          </span>
        );
      })}
    </div>
  );
}
