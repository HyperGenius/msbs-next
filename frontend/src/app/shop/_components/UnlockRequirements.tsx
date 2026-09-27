/** 未解放の商品について、足りない解放条件（設計図・技術Lv）を示す */
"use client";

import { BlueprintUnlockState } from "@/types/battle";
import { formatMissingTech } from "@/utils/technology";

interface UnlockRequirementsProps {
  listing: BlueprintUnlockState;
}

export default function UnlockRequirements({ listing }: UnlockRequirementsProps) {
  const missingTechs = listing.missing_tech_requirements;
  if (!listing.unlock_hint && missingTechs.length === 0) return null;

  return (
    <ul className="mb-2 space-y-1 text-xs text-center">
      {listing.unlock_hint && (
        <li className="text-[#00ff41]/60">{listing.unlock_hint}</li>
      )}
      {missingTechs.map((requirement) => (
        <li key={requirement.tech_id} className="text-[#ffb000]">
          {formatMissingTech(requirement)}
        </li>
      ))}
    </ul>
  );
}
