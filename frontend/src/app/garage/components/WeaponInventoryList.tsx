/* frontend/src/app/garage/components/WeaponInventoryList.tsx */
"use client";

import { useMemo, useState } from "react";
import { PlayerWeapon, Weapon } from "@/types/battle";
import { EnrichedMobileSuit } from "@/utils/rankUtils";
import { SciFiButton, SciFiCard, SciFiHeading, SciFiPanel, SciFiSelect } from "@/components/ui";
import { getRankColor, getWeaponRank } from "@/utils/rankUtils";
import { getWeaponSlots } from "../constants";

type TypeFilter = "ALL" | "BEAM" | "PHYSICAL";
type EquipFilter = "ALL" | "UNEQUIPPED_ONLY";
type SortOrder = "ACQUIRED_DESC" | "ACQUIRED_ASC" | "EQUIPPED_FIRST";

interface WeaponInventoryListProps {
  playerWeapons: PlayerWeapon[] | undefined;
  mobileSuits: EnrichedMobileSuit[] | undefined;
  isBusy: boolean;
  onNavigateToEquippedMs: (msId: string) => void;
  onEquip: (playerWeaponId: string, msId: string, slotIndex: number) => void;
}

/** base_snapshot / custom_stats を Weapon スペックとして安全に解決する（改造差分は現状常に空） */
function resolveSpec(pw: PlayerWeapon): Weapon {
  return pw.base_snapshot as unknown as Weapon;
}

export default function WeaponInventoryList({
  playerWeapons,
  mobileSuits,
  isBusy,
  onNavigateToEquippedMs,
  onEquip,
}: WeaponInventoryListProps) {
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("ALL");
  const [equipFilter, setEquipFilter] = useState<EquipFilter>("ALL");
  const [sortOrder, setSortOrder] = useState<SortOrder>("ACQUIRED_DESC");

  const rows = useMemo(() => {
    if (!playerWeapons) return [];

    const filtered = playerWeapons.filter((pw) => {
      const spec = resolveSpec(pw);
      if (typeFilter !== "ALL" && (spec.type || "PHYSICAL") !== typeFilter) {
        return false;
      }
      if (equipFilter === "UNEQUIPPED_ONLY" && pw.equipped_ms_id !== null) {
        return false;
      }
      return true;
    });

    return [...filtered].sort((a, b) => {
      if (sortOrder === "EQUIPPED_FIRST") {
        const aEquipped = a.equipped_ms_id !== null ? 0 : 1;
        const bEquipped = b.equipped_ms_id !== null ? 0 : 1;
        if (aEquipped !== bEquipped) return aEquipped - bEquipped;
      }
      const aTime = new Date(a.acquired_at).getTime();
      const bTime = new Date(b.acquired_at).getTime();
      return sortOrder === "ACQUIRED_ASC" ? aTime - bTime : bTime - aTime;
    });
  }, [playerWeapons, typeFilter, equipFilter, sortOrder]);

  return (
    <SciFiPanel variant="primary">
      <div className="p-4 sm:p-6">
        <SciFiHeading level={3} className="mb-4 text-lg sm:text-xl">
          所持武器一覧
        </SciFiHeading>

        {/* フィルタ・並び替え */}
        <div className="flex flex-wrap gap-2 mb-4">
          <SciFiButton
            variant={equipFilter === "UNEQUIPPED_ONLY" ? "accent" : "primary"}
            size="sm"
            onClick={() =>
              setEquipFilter((prev) =>
                prev === "UNEQUIPPED_ONLY" ? "ALL" : "UNEQUIPPED_ONLY"
              )
            }
          >
            未装備のみ表示
          </SciFiButton>

          <SciFiSelect
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as TypeFilter)}
            options={[
              { value: "ALL", label: "属性: すべて" },
              { value: "BEAM", label: "属性: BEAM" },
              { value: "PHYSICAL", label: "属性: PHYSICAL" },
            ]}
          />

          <SciFiSelect
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as SortOrder)}
            options={[
              { value: "ACQUIRED_DESC", label: "取得日時: 新しい順" },
              { value: "ACQUIRED_ASC", label: "取得日時: 古い順" },
              { value: "EQUIPPED_FIRST", label: "装備中を上に表示" },
            ]}
          />
        </div>

        {rows.length === 0 ? (
          <p className="text-[#00ff41]/50 text-sm">
            条件に一致する所持武器がありません。
          </p>
        ) : (
          <ul className="space-y-2">
            {rows.map((pw) => (
              <WeaponInventoryRow
                key={pw.id}
                playerWeapon={pw}
                mobileSuits={mobileSuits}
                isBusy={isBusy}
                onNavigateToEquippedMs={onNavigateToEquippedMs}
                onEquip={onEquip}
              />
            ))}
          </ul>
        )}
      </div>
    </SciFiPanel>
  );
}

interface WeaponInventoryRowProps {
  playerWeapon: PlayerWeapon;
  mobileSuits: EnrichedMobileSuit[] | undefined;
  isBusy: boolean;
  onNavigateToEquippedMs: (msId: string) => void;
  onEquip: (playerWeaponId: string, msId: string, slotIndex: number) => void;
}

function WeaponInventoryRow({
  playerWeapon,
  mobileSuits,
  isBusy,
  onNavigateToEquippedMs,
  onEquip,
}: WeaponInventoryRowProps) {
  const spec = resolveSpec(playerWeapon);
  const isEquipped = playerWeapon.equipped_ms_id !== null;
  const equippedMs = isEquipped
    ? mobileSuits?.find((ms) => ms.id === playerWeapon.equipped_ms_id)
    : undefined;

  const [selectedMsId, setSelectedMsId] = useState<string>("");
  const [selectedSlot, setSelectedSlot] = useState<number>(0);

  const powerRank = spec.power_rank ?? getWeaponRank("weapon_power", spec.power);
  const rangeRank = spec.range_rank ?? getWeaponRank("weapon_range", spec.range);
  const accuracyRank =
    spec.accuracy_rank ?? getWeaponRank("weapon_accuracy", spec.accuracy);

  const selectedMs = mobileSuits?.find((ms) => ms.id === selectedMsId);
  const slots = getWeaponSlots(selectedMs?.weapon_slot_count);

  return (
    <SciFiCard variant="primary" className="p-3 sm:p-4">
      <div className="flex justify-between items-start gap-3">
        <div>
          <div className="font-bold text-base sm:text-lg">{spec.name}</div>
          <div className="text-xs sm:text-sm text-[#00ff41]/70 mt-1 flex gap-3">
            <span className={`font-bold ${getRankColor(powerRank)}`}>
              威力: {powerRank}
            </span>
            <span className={`font-bold ${getRankColor(rangeRank)}`}>
              射程: {rangeRank}
            </span>
            <span className={`font-bold ${getRankColor(accuracyRank)}`}>
              命中: {accuracyRank}
            </span>
          </div>
        </div>
        <span
          className={`shrink-0 px-2 py-1 text-xs font-bold rounded ${
            spec.type === "BEAM"
              ? "bg-blue-500/20 text-blue-400"
              : "bg-yellow-500/20 text-yellow-400"
          }`}
        >
          {spec.type || "PHYSICAL"}
        </span>
      </div>

      <div className="mt-2 text-xs sm:text-sm">
        {isEquipped ? (
          equippedMs ? (
            <SciFiButton
              variant="primary"
              size="sm"
              onClick={() => onNavigateToEquippedMs(equippedMs.id)}
            >
              → {equippedMs.name} へ移動（スロット
              {(playerWeapon.equipped_slot ?? 0) + 1}）
            </SciFiButton>
          ) : (
            <span className="font-bold text-[#ffb000]">
              装備先: 不明な機体
            </span>
          )
        ) : (
          <span className="text-[#00ff41]/50">未装備</span>
        )}
      </div>

      {!isEquipped && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <SciFiSelect
            value={selectedMsId}
            onChange={(e) => {
              setSelectedMsId(e.target.value);
              setSelectedSlot(0);
            }}
            options={[
              { value: "", label: "装備先の機体を選択" },
              ...(mobileSuits?.map((ms) => ({ value: ms.id, label: ms.name })) ?? []),
            ]}
          />

          {selectedMsId && (
            <SciFiSelect
              value={selectedSlot}
              onChange={(e) => setSelectedSlot(Number(e.target.value))}
              options={slots.map((slot) => ({
                value: slot.index,
                label: slot.labelJa,
              }))}
            />
          )}

          <SciFiButton
            variant="accent"
            size="sm"
            disabled={!selectedMsId || isBusy}
            onClick={() =>
              onEquip(playerWeapon.id, selectedMsId, selectedSlot)
            }
          >
            装備する
          </SciFiButton>
        </div>
      )}
    </SciFiCard>
  );
}
