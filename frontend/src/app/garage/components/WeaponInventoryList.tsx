/* frontend/src/app/garage/components/WeaponInventoryList.tsx */
"use client";

import { useMemo, useState } from "react";
import { PlayerWeapon, Pilot } from "@/types/battle";
import { EnrichedMobileSuit } from "@/utils/rankUtils";
import { SciFiButton, SciFiCard, SciFiHeading, SciFiPanel, SciFiSelect } from "@/components/ui";
import { getWeaponRank } from "@/utils/rankUtils";
import { getWeaponSlotLabel } from "../constants";
import { countUpgradeSteps, resolveWeaponSpec } from "../weaponUpgrade";
import { usePlayerWeapons } from "@/hooks/usePlayerWeapons";
import WeaponResourceBadges from "./WeaponResourceBadges";
import WeaponUpgradeModal, { WeaponModalTab } from "./WeaponUpgradeModal";

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

/** カードを押すと改造モーダルが開くことを示すアイコン（右向き山括弧） */
function ChevronRightIcon({ className }: { className?: string }) {
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
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

interface WeaponInventoryListProps {
  mobileSuits: EnrichedMobileSuit[] | undefined;
  isBusy: boolean;
  pilot: Pilot | undefined;
  onNavigateToEquippedMs: (msId: string) => void;
  /** 装備に成功したら true を返す */
  onEquip: (playerWeaponId: string, msId: string, slotIndex: number) => Promise<boolean>;
  /** 武器改造モーダルでの改造成功時に呼ばれる（呼び出し元でパイロットのクレジット残高を再検証する。所持武器一覧自体は本コンポーネントが自分のSWRキーで再検証する） */
  onWeaponUpgraded: () => void;
}

export default function WeaponInventoryList({
  mobileSuits,
  isBusy,
  pilot,
  onNavigateToEquippedMs,
  onEquip,
  onWeaponUpgraded,
}: WeaponInventoryListProps) {
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("ALL");
  const [equipFilter, setEquipFilter] = useState<EquipFilter>("ALL");
  const [sortOrder, setSortOrder] = useState<SortOrder>("ACQUIRED_DESC");
  const [sortMenuOpen, setSortMenuOpen] = useState(false);
  // 改造モーダルで表示中の武器と、開いたときのタブ（null なら非表示）
  const [modalTarget, setModalTarget] = useState<{
    playerWeapon: PlayerWeapon;
    initialTab: WeaponModalTab;
  } | null>(null);

  // 「未装備のみ表示」がONの場合は GET /api/player-weapons?unequipped=true を使い、
  // 装備済みも含めた全件取得を避ける（同一URLのSWRキーはアプリ内で共有されるため、
  // OFF時の全件フェッチは他画面のキャッシュと重複排除される）
  const { playerWeapons, mutate: mutatePlayerWeapons } = usePlayerWeapons(
    equipFilter === "UNEQUIPPED_ONLY"
  );

  const msById = useMemo(() => {
    const map = new Map<string, EnrichedMobileSuit>();
    mobileSuits?.forEach((ms) => map.set(ms.id, ms));
    return map;
  }, [mobileSuits]);

  const isFiltered = typeFilter !== "ALL" || equipFilter !== "ALL";

  const rows = useMemo(() => {
    if (!playerWeapons) return [];

    const filtered = playerWeapons.filter((pw) => {
      const spec = resolveWeaponSpec(pw);
      if (typeFilter !== "ALL" && (spec.type || "PHYSICAL") !== typeFilter) {
        return false;
      }
      // equipFilter は基本的にサーバー側（unequipped=true）で反映済みだが、
      // 直後の再検証タイミングのずれに備えてクライアント側でも保険としてフィルタする
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

  // 装備した際、このコンポーネントが保持するSWRキャッシュ（未装備のみ/全件）を再検証する。
  // 装備後はカードの「装備先へ移動」ボタンが結果を示すので、モーダルは閉じる。
  const handleEquip = async (
    playerWeaponId: string,
    msId: string,
    slotIndex: number
  ) => {
    const equipped = await onEquip(playerWeaponId, msId, slotIndex);
    mutatePlayerWeapons();
    if (equipped) setModalTarget(null);
    return equipped;
  };

  // 装備先の CustomizationModal はこのモーダルと同じ z-index なので、先に閉じてから開く
  const handleNavigateFromModal = (msId: string) => {
    setModalTarget(null);
    onNavigateToEquippedMs(msId);
  };

  // 武器改造成功時: モーダル内の表示を更新し、現在のフィルタ状態に対応するSWRキーの
  // 所持武器一覧を再検証する（パイロットのクレジット残高の再検証は onWeaponUpgraded 側の責務）
  const handleWeaponUpgraded = (updated: PlayerWeapon) => {
    setModalTarget((prev) => (prev ? { ...prev, playerWeapon: updated } : prev));
    mutatePlayerWeapons();
    onWeaponUpgraded();
  };

  return (
    <>
      {/* モバイルではパネルを親の残り高さに合わせ、カードのリストだけをスクロールさせる。
          md 以上はページ全体のスクロールに任せる（ルートレイアウトが md 以上で main の高さ固定を外すため）。 */}
      <SciFiPanel variant="primary" className="flex flex-col flex-1 min-h-0 md:flex-none">
      <div className="flex flex-col flex-1 min-h-0 p-3 sm:p-6">
        <div className="shrink-0 flex items-baseline justify-between mb-2 sm:mb-3">
          <SciFiHeading level={3} className="text-base sm:text-xl">
            所持武器一覧
          </SciFiHeading>
          {playerWeapons && (
            <span className="text-xs text-[#00ff41]/50">
              {rows.length}
              {/* 未装備のみ表示ON時は playerWeapons 自体がサーバー側で絞り込み済みのため、
                  母数として使えるのは属性フィルタのみが効いている場合に限る */}
              {typeFilter !== "ALL" && equipFilter === "ALL"
                ? ` / ${playerWeapons.length}`
                : ""}
              件
            </span>
          )}
        </div>

        {/* フィルタ: 使用頻度の高い2つ（未装備のみ／属性）だけを常時表示し、
            並び替えはアイコンボタンからポップアップメニューで選ばせる（1行に3種のUIを混在させない） */}
        <div className="shrink-0 flex items-center gap-2 mb-3 sm:mb-4">
          <button
            type="button"
            title="未装備のみ表示"
            aria-pressed={equipFilter === "UNEQUIPPED_ONLY"}
            onClick={() =>
              setEquipFilter((prev) =>
                prev === "UNEQUIPPED_ONLY" ? "ALL" : "UNEQUIPPED_ONLY"
              )
            }
            className={`flex items-center gap-1.5 min-h-11 px-3 text-xs font-bold border-2 transition-colors whitespace-nowrap ${
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
              onChange={(v) => setTypeFilter(v as TypeFilter)}
              className="!w-auto !px-2 !py-2 !text-xs min-h-11"
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
              aria-haspopup="menu"
              aria-expanded={sortMenuOpen}
              onClick={() => setSortMenuOpen((prev) => !prev)}
              className={`flex items-center justify-center w-11 h-11 border-2 transition-colors ${
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
                <div
                  role="menu"
                  aria-label="並び替え"
                  className="absolute right-0 z-50 mt-1 w-44 border-2 border-[#00ff41]/50 bg-[#0a0a0a] shadow-lg"
                >
                  {SORT_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      role="menuitem"
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
          // px-1/py-1 は hover 時の scale-[1.02] でカードの縁がスクロール領域に切られないための余白
          <ul className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden md:overflow-visible -mx-1 px-1 py-1 space-y-2">
            {rows.map((pw) => (
              <WeaponInventoryRow
                key={pw.id}
                playerWeapon={pw}
                msById={msById}
                onNavigateToEquippedMs={onNavigateToEquippedMs}
                onOpenModal={(initialTab) => setModalTarget({ playerWeapon: pw, initialTab })}
              />
            ))}
          </ul>
        )}
      </div>
      </SciFiPanel>

      {modalTarget && (
        <WeaponUpgradeModal
          playerWeapon={modalTarget.playerWeapon}
          pilot={pilot}
          mobileSuits={mobileSuits}
          isBusy={isBusy}
          initialTab={modalTarget.initialTab}
          onClose={() => setModalTarget(null)}
          onUpgraded={handleWeaponUpgraded}
          onEquip={handleEquip}
          onNavigateToEquippedMs={handleNavigateFromModal}
        />
      )}
    </>
  );
}

interface WeaponInventoryRowProps {
  playerWeapon: PlayerWeapon;
  msById: Map<string, EnrichedMobileSuit>;
  onNavigateToEquippedMs: (msId: string) => void;
  /** カード本体は改造タブ、「装備する」ボタンは装備タブを指定してモーダルを開く */
  onOpenModal: (initialTab: WeaponModalTab) => void;
}

const CARD_ACTION_BUTTON_CLASS =
  "min-h-11 border border-[#00ff41] text-[#00ff41] bg-transparent hover:bg-[#00ff41] hover:text-black active:bg-[#00ff41] active:text-black transition-colors font-bold font-mono text-sm px-4 py-2";

function WeaponInventoryRow({
  playerWeapon,
  msById,
  onNavigateToEquippedMs,
  onOpenModal,
}: WeaponInventoryRowProps) {
  const spec = resolveWeaponSpec(playerWeapon);
  const upgradeSteps = countUpgradeSteps(playerWeapon);
  const isEquipped = playerWeapon.equipped_ms_id !== null;
  const equippedMs = playerWeapon.equipped_ms_id
    ? msById.get(playerWeapon.equipped_ms_id)
    : undefined;

  const powerRank = spec.power_rank ?? getWeaponRank("weapon_power", spec.power);
  const rangeRank = spec.range_rank ?? getWeaponRank("weapon_range", spec.range);
  const accuracyRank =
    spec.accuracy_rank ?? getWeaponRank("weapon_accuracy", spec.accuracy);

  return (
    // SciFiCard の既定の p-6 が p-3 より優先されるため、important で上書きする
    <SciFiCard
      variant="primary"
      className="!p-3"
      interactive
      onClick={() => onOpenModal("UPGRADE")}
    >
      <div className="flex items-center gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-bold text-base sm:text-lg break-words min-w-0">
                {spec.name}
              </span>
              {upgradeSteps > 0 && (
                <span
                  className="shrink-0 px-1.5 py-0.5 text-xs font-bold border rounded bg-[#00f0ff]/10 text-[#00f0ff] border-[#00f0ff]/50"
                  title={`改造済み（${upgradeSteps}段階）`}
                >
                  改+{upgradeSteps}
                </span>
              )}
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

          <div className="mt-2 flex flex-wrap gap-2">
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
            <WeaponResourceBadges spec={spec} />
          </div>

          {/* カード内のボタンはカード本体のクリック（改造モーダルを開く）と別の操作なので、伝播を止める */}
          <div className="mt-2">
            {isEquipped ? (
              equippedMs ? (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onNavigateToEquippedMs(equippedMs.id);
                  }}
                  className={`w-full ${CARD_ACTION_BUTTON_CLASS}`}
                >
                  → {equippedMs.name}へ移動（
                  {getWeaponSlotLabel(playerWeapon.equipped_slot ?? 0)}）
                </button>
              ) : (
                <span className="text-xs sm:text-sm font-bold text-[#ffb000]">
                  装備先: 不明な機体
                </span>
              )
            ) : (
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs sm:text-sm text-[#00ff41]/50">未装備</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenModal("EQUIP");
                  }}
                  className={CARD_ACTION_BUTTON_CLASS}
                >
                  装備する
                </button>
              </div>
            )}
          </div>
        </div>

        <ChevronRightIcon className="w-5 h-5 shrink-0 text-[#00ff41]/50" />
      </div>
    </SciFiCard>
  );
}
