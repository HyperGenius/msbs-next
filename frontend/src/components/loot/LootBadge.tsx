/* frontend/src/components/loot/LootBadge.tsx */
import { LootItem } from "@/types/battle";
import { IconFileCertificate } from "@/components/icons/TablerIcons";

interface LootBadgeProps {
  loot: LootItem[] | null | undefined;
}

/**
 * バトル履歴の一覧で、戦利品のあったバトルに付けるバッジ。
 * 新規入手が1件でもあれば NEW を表示し、換金のみなら換金額の合計を表示する。
 */
export default function LootBadge({ loot }: LootBadgeProps) {
  if (!loot || loot.length === 0) return null;

  const hasNew = loot.some((item) => item.is_new);
  const credits = loot.reduce((sum, item) => sum + item.credits_awarded, 0);
  const names = loot.map((item) => item.target_name).join("、");

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-bold font-mono border ${
        hasNew
          ? "border-[#00f0ff] text-[#00f0ff] bg-[#00f0ff]/10"
          : "border-[#ffb000]/50 text-[#ffb000] bg-[#ffb000]/5"
      }`}
      title={`戦利品: ${names}`}
      aria-label={`戦利品: ${names}`}
    >
      <IconFileCertificate className="w-3.5 h-3.5" />
      {hasNew ? "NEW" : `+${credits.toLocaleString()} C`}
    </span>
  );
}
