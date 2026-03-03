import { MobileSuit } from "@/types/battle";
import { STATUS_LABELS } from "@/utils/displayUtils";
import { getRankColor } from "@/utils/rankUtils";

const RANK_ITEMS: { label: string; key: keyof Pick<MobileSuit, "hp_rank" | "armor_rank" | "mobility_rank"> }[] = [
  { label: STATUS_LABELS.hp, key: "hp_rank" },
  { label: STATUS_LABELS.armor, key: "armor_rank" },
  { label: STATUS_LABELS.mobility, key: "mobility_rank" },
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
          <span key={key} className="flex items-center gap-1 text-gray-400 pt-1">
            {label}:
            <span className={`font-bold ${getRankColor(rank)}`}>{rank}</span>
          </span>
        );
      })}
    </div>
  );
}
