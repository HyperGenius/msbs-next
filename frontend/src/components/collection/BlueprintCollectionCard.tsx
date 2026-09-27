/* frontend/src/components/collection/BlueprintCollectionCard.tsx */
import { BlueprintCollectionItem } from "@/types/battle";
import { IconFileCertificate } from "@/components/icons/TablerIcons";
import { LOOT_TARGET_LABELS } from "@/components/loot/LootItemCard";
import {
  BLUEPRINT_SOURCE_LABELS,
  COLLECTION_STATUS_LABELS,
  CollectionStatus,
  FACTION_LABELS,
  OTHER_FACTION_MESSAGE,
  UNAVAILABLE_MESSAGE,
  collectionStatus,
  formatTheater,
  obtainabilityOf,
} from "@/utils/blueprintCollection";
import { formatMissingTech, unmetTechRequirements } from "@/utils/technology";

// 所持は LootItemCard の新規入手と同じシアンにそろえる。
const CARD_TONES: Record<CollectionStatus, string> = {
  owned: "border-[#00f0ff]/60 bg-[#00f0ff]/5 text-[#00f0ff]",
  unowned: "border-[#00ff41]/30 bg-[#0a0a0a] text-[#00ff41]/60",
  standard: "border-gray-700 bg-[#0a0a0a] text-gray-500",
};

const BADGE_TONES: Record<CollectionStatus, string> = {
  owned: "bg-[#00f0ff] text-black border-[#00f0ff]",
  unowned: "border-[#00ff41]/40 text-[#00ff41]/70",
  standard: "border-gray-600 text-gray-400",
};

const FACTION_TONES: Record<string, string> = {
  FEDERATION: "text-[#00f0ff]",
  ZEON: "text-[#ffb000]",
};

interface BlueprintCollectionCardProps {
  item: BlueprintCollectionItem;
}

/** 設計図コレクション（図鑑）の1件を表示するカード */
export default function BlueprintCollectionCard({ item }: BlueprintCollectionCardProps) {
  const status = collectionStatus(item);

  return (
    <div
      className={`flex items-start gap-3 border px-3 py-2 font-mono ${CARD_TONES[status]}`}
      data-testid="blueprint-collection-card"
    >
      <IconFileCertificate
        className={`w-7 h-7 shrink-0 mt-1 ${status === "owned" ? "" : "opacity-40"}`}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[10px] tracking-widest">
          <span className="opacity-70">{LOOT_TARGET_LABELS[item.target_type]}</span>
          {item.faction && (
            <span className={FACTION_TONES[item.faction] ?? "opacity-70"}>
              {FACTION_LABELS[item.faction] ?? item.faction}
            </span>
          )}
        </div>
        <p
          className={`text-sm sm:text-base font-bold truncate ${
            status === "owned" ? "text-white" : "text-gray-300"
          }`}
          title={item.target_name}
        >
          {item.target_name}
        </p>
        <BlueprintCollectionDetail item={item} status={status} />
      </div>
      <span
        className={`shrink-0 border text-[10px] font-bold px-1.5 py-0.5 tracking-widest ${BADGE_TONES[status]}`}
      >
        {COLLECTION_STATUS_LABELS[status]}
      </span>
    </div>
  );
}

/** 状態に応じた補足（入手日・入手経路・足りない技術Lv、または入手先） */
function BlueprintCollectionDetail({
  item,
  status,
}: {
  item: BlueprintCollectionItem;
  status: CollectionStatus;
}) {
  if (status === "standard") {
    return <p className="text-[11px] opacity-80">設計図なしで購入できます</p>;
  }

  if (status === "owned") {
    const unmet = unmetTechRequirements(item.tech_requirements);
    return (
      <>
        <p className="text-[11px] opacity-80">
          {item.acquired_at && (
            <span>入手日 {new Date(item.acquired_at).toLocaleDateString("ja-JP")}</span>
          )}
          {item.source && (
            <span className="ml-2">{BLUEPRINT_SOURCE_LABELS[item.source] ?? item.source}</span>
          )}
        </p>
        {unmet.length > 0 && (
          <ul className="mt-0.5 text-[11px] text-[#ffb000]">
            {unmet.map((requirement) => (
              <li key={requirement.tech_id}>{formatMissingTech(requirement)}</li>
            ))}
          </ul>
        )}
      </>
    );
  }

  const obtainability = obtainabilityOf(item);
  if (obtainability?.kind === "other_faction") {
    return <p className="text-[11px] text-red-400/80">{OTHER_FACTION_MESSAGE}</p>;
  }
  if (obtainability?.kind !== "theaters") {
    return <p className="text-[11px] opacity-60">{UNAVAILABLE_MESSAGE}</p>;
  }
  return (
    <div className="flex flex-wrap items-center gap-1 mt-0.5 text-[11px]">
      <span className="opacity-70">入手先</span>
      {obtainability.theaters.map((theater) => (
        <span
          key={theater.label}
          className="border border-[#00ff41]/40 px-1.5 text-[#00ff41]"
        >
          {formatTheater(theater)}
        </span>
      ))}
    </div>
  );
}
