/* frontend/src/app/garage/components/WeaponInventoryList.tsx */
"use client";

import { useMemo, useState } from "react";
import { PlayerWeapon, Weapon } from "@/types/battle";
import { EnrichedMobileSuit } from "@/utils/rankUtils";
import { SciFiButton, SciFiCard, SciFiHeading, SciFiPanel, SciFiSelect } from "@/components/ui";
import { getWeaponRank } from "@/utils/rankUtils";
import { getWeaponSlots } from "../constants";

type TypeFilter = "ALL" | "BEAM" | "PHYSICAL";
type EquipFilter = "ALL" | "UNEQUIPPED_ONLY";
type SortOrder = "ACQUIRED_DESC" | "ACQUIRED_ASC" | "EQUIPPED_FIRST";

const SORT_OPTIONS: { value: SortOrder; label: string }[] = [
  { value: "ACQUIRED_DESC", label: "取得日時: 新しい順" },
  { value: "ACQUIRED_ASC", label: "取得日時: 古い順" },
  { value: "EQUIPPED_FIRST", label: "装備中が上" },
];

/** ランク文字（S〜E）を背景付きバッジのスタイルに変換する（テキスト色だけだと視認性が低いため） */
const RANK_BADGE_CLASSES: Record<string, string> = {
  S: "bg-green-400/15 text-green-300 border-green-400/50",
  A: "bg-blue-400/15 text-blue-300 border-blue-400/50",
  B: "bg-yellow-400/15 text-yellow-300 border-yellow-400/50",
  C: "bg-orange-400/15 text-orange-300 border-orange-400/50",
  D: "bg-red-400/15 text-red-300 border-red-400/50",
  E: "bg-red-900/40 text-red-500 border-red-800/60",
};

function rankBadgeClass(rank: string): string {
  return RANK_BADGE_CLASSES[rank] ?? "bg-gray-400/15 text-gray-300 border-gray-400/50";
}

/** 未装備のみ表示トグル用のフィルタアイコン（漏斗） */
function FilterIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M4 5h16M7 12h10M11 19h2" />
    </svg>
  );
}

/** 属性フィルタ用のアイコン（着弾点） */
function TypeIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      className={className}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** 並び替え用のアイコン（上下矢印） */
function SortIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M8 4v16M8 4 5 7M8 4l3 3M16 20V4M16 20l-3-3M16 20l3-3" />
    </svg>
  );
}

/** 空状態表示用のアイコン（武器箱） */
function EmptyBoxIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M3 8l9-5 9 5-9 5-9-5Z" />
      <path d="M3 8v8l9 5 9-5V8" />
      <path d="M12 13v8" />
    </svg>
  );
}

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
  const [sortMenuOpen, setSortMenuOpen] = useState(false);

  const isFiltered = typeFilter !== "ALL" || equipFilter !== "ALL";

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

  const resetFilters = () => {
    setTypeFilter("ALL");
    setEquipFilter("ALL");
  };

  return (
    <SciFiPanel variant="primary">
      <div className="p-4 sm:p-6">
        <div className="flex items-baseline justify-between mb-3">
          <SciFiHeading level={3} className="text-lg sm:text-xl">
            所持武器一覧
          </SciFiHeading>
          {playerWeapons && (
            <span className="text-xs text-[#00ff41]/50">
              {rows.length}
              {isFiltered ? ` / ${playerWeapons.length}` : ""}件
            </span>
          )}
        </div>

        {/* フィルタ: 使用頻度の高い2つ（未装備のみ／属性）だけを常時表示し、
            並び替えはアイコンボタンからポップアップメニューで選ばせる（1行に3種のUIを混在させない） */}
        <div className="flex items-center gap-2 mb-4">
          <button
            type="button"
            title="未装備のみ表示"
            aria-pressed={equipFilter === "UNEQUIPPED_ONLY"}
            onClick={() =>
              setEquipFilter((prev) =>
                prev === "UNEQUIPPED_ONLY" ? "ALL" : "UNEQUIPPED_ONLY"
              )
            }
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-bold border-2 transition-colors whitespace-nowrap ${
              equipFilter === "UNEQUIPPED_ONLY"
                ? "bg-[#00ff41] text-black border-[#00ff41]"
                : "bg-transparent text-[#00ff41] border-[#00ff41]/40 hover:border-[#00ff41]"
            }`}
          >
            <FilterIcon className="w-4 h-4" />
            未装備のみ
          </button>

          <div className="flex items-center gap-1.5">
            <TypeIcon className="w-4 h-4 text-[#00ff41]/60 shrink-0" />
            <SciFiSelect
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as TypeFilter)}
              className="!w-auto !px-2 !py-2 !text-xs"
              options={[
                { value: "ALL", label: "属性: すべて" },
                { value: "BEAM", label: "BEAM" },
                { value: "PHYSICAL", label: "PHYSICAL" },
              ]}
            />
          </div>

          {/* 並び替え: 使用頻度が低いため、アイコンボタン+ポップアップメニューに格納 */}
          <div className="relative ml-auto">
            <button
              type="button"
              title="並び替え"
              aria-haspopup="listbox"
              aria-expanded={sortMenuOpen}
              onClick={() => setSortMenuOpen((prev) => !prev)}
              className={`flex items-center justify-center w-9 h-9 border-2 transition-colors ${
                sortMenuOpen
                  ? "bg-[#00ff41]/20 border-[#00ff41] text-[#00ff41]"
                  : "bg-transparent border-[#00ff41]/40 text-[#00ff41]/70 hover:border-[#00ff41] hover:text-[#00ff41]"
              }`}
            >
              <SortIcon className="w-4 h-4" />
            </button>

            {sortMenuOpen && (
              <>
                {/* 外側クリックで閉じるための透明な背景 */}
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setSortMenuOpen(false)}
                />
                <div className="absolute right-0 z-50 mt-1 w-44 border-2 border-[#00ff41]/50 bg-[#0a0a0a] shadow-lg">
                  {SORT_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => {
                        setSortOrder(opt.value);
                        setSortMenuOpen(false);
                      }}
                      className={`block w-full text-left px-3 py-2 text-xs whitespace-nowrap ${
                        sortOrder === opt.value
                          ? "bg-[#00ff41]/20 text-[#00ff41] font-bold"
                          : "text-[#00ff41]/70 hover:bg-[#00ff41]/10"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {rows.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-10 text-center">
            <EmptyBoxIcon className="w-10 h-10 text-[#00ff41]/30" />
            <p className="text-[#00ff41]/50 text-sm">
              {isFiltered
                ? "条件に一致する所持武器がありません。"
                : "所持している武器がありません。ショップで武器を購入してください。"}
            </p>
            {isFiltered && (
              <SciFiButton variant="primary" size="sm" onClick={resetFilters}>
                フィルタをリセット
              </SciFiButton>
            )}
          </div>
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
    <SciFiCard variant="primary" className="p-3">
      <div className="flex justify-between items-start gap-3">
        <div className="font-bold text-base sm:text-lg">{spec.name}</div>
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

      <div className="mt-2 flex gap-2">
        <span
          className={`px-1.5 py-0.5 text-xs font-bold border rounded ${rankBadgeClass(powerRank)}`}
        >
          威力{powerRank}
        </span>
        <span
          className={`px-1.5 py-0.5 text-xs font-bold border rounded ${rankBadgeClass(rangeRank)}`}
        >
          射程{rangeRank}
        </span>
        <span
          className={`px-1.5 py-0.5 text-xs font-bold border rounded ${rankBadgeClass(accuracyRank)}`}
        >
          命中{accuracyRank}
        </span>
      </div>

      <div className="mt-2">
        {isEquipped ? (
          equippedMs ? (
            <button
              type="button"
              onClick={() => onNavigateToEquippedMs(equippedMs.id)}
              className="w-full border border-[#00ff41] text-[#00ff41] bg-transparent hover:bg-[#00ff41] hover:text-black active:bg-[#00ff41] active:text-black transition-colors font-bold font-mono text-sm px-4 py-2.5"
            >
              → {equippedMs.name}へ移動（スロット
              {(playerWeapon.equipped_slot ?? 0) + 1}）
            </button>
          ) : (
            <span className="text-xs sm:text-sm font-bold text-[#ffb000]">
              装備先: 不明な機体
            </span>
          )
        ) : (
          <span className="text-xs sm:text-sm text-[#00ff41]/50">未装備</span>
        )}
      </div>

      {!isEquipped && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
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
