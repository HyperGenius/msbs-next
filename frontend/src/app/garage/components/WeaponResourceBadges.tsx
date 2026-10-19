/* frontend/src/app/garage/components/WeaponResourceBadges.tsx */

import { Weapon } from "@/types/battle";

interface WeaponResourceBadgesProps {
  spec: Pick<Weapon, "max_ammo" | "en_cost">;
}

const BADGE_CLASS =
  "px-1.5 py-0.5 text-xs font-bold border rounded bg-[#00ff41]/5 text-[#00ff41]/80 border-[#00ff41]/30";

/**
 * 弾数と 1 射ごとの EN 消費をバッジで表示する。
 * ランクではなく実数なので、ランク色を使わない中立の配色にする。
 */
export default function WeaponResourceBadges({ spec }: WeaponResourceBadgesProps) {
  // エンジンは max_ammo が null・0 のとき弾数を無制限として扱う
  const ammoLabel = spec.max_ammo ? String(spec.max_ammo) : "∞";
  const enCost = spec.en_cost ?? 0;

  return (
    <>
      <span className={BADGE_CLASS}>弾数{ammoLabel}</span>
      {enCost > 0 && <span className={BADGE_CLASS}>EN{enCost}</span>}
    </>
  );
}
