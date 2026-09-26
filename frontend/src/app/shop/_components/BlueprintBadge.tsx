/** 設計図による解放状態のバッジ: 未解放・設計図所持を示す */
"use client";

import { BlueprintUnlockState } from "@/types/battle";
import { getBlueprintBadgeKind } from "../utils";

const BADGE_STYLES = {
  locked: {
    label: "未解放",
    className: "border-[#00ff41]/40 text-[#00ff41]/60 bg-[#0a0a0a]",
  },
  blueprint_owned: {
    label: "設計図所持",
    className: "border-[#00f0ff]/60 text-[#00f0ff] bg-[#00f0ff]/10",
  },
} as const;

interface BlueprintBadgeProps {
  listing: BlueprintUnlockState;
}

export default function BlueprintBadge({ listing }: BlueprintBadgeProps) {
  const kind = getBlueprintBadgeKind(listing);
  if (!kind) return null;

  const { label, className } = BADGE_STYLES[kind];
  return (
    <span className={`shrink-0 px-1.5 py-0.5 text-[10px] font-bold font-mono border ${className}`}>
      {label}
    </span>
  );
}
