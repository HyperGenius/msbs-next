/* frontend/src/app/collection/page.tsx */
"use client";

import { useState } from "react";
import { useBlueprintCollection } from "@/services/api";
import { BlueprintCollectionItem } from "@/types/battle";
import { SciFiButton, SciFiPanel } from "@/components/ui";
import BlueprintCollectionCard from "@/components/collection/BlueprintCollectionCard";
import {
  COLLECTION_STATUS_LABELS,
  CollectionFilter,
  CollectionProgress,
  collectionProgress,
  collectionStatus,
  filterAndSortCollection,
} from "@/utils/blueprintCollection";

type TabType = BlueprintCollectionItem["target_type"];

const TABS: { value: TabType; label: string }[] = [
  { value: "MOBILE_SUIT", label: "Mobile Suits" },
  { value: "WEAPON", label: "Weapons" },
];

const FILTERS: CollectionFilter[] = ["all", "unowned", "owned", "standard"];

/** 設計図コレクション（図鑑）ページ */
export default function CollectionPage() {
  const { collection, isLoading, isError } = useBlueprintCollection();
  const [activeTab, setActiveTab] = useState<TabType>("MOBILE_SUIT");
  const [filter, setFilter] = useState<CollectionFilter>("all");

  const all = collection ?? [];
  const tabItems = all.filter((item) => item.target_type === activeTab);
  const visibleItems = filterAndSortCollection(tabItems, filter);
  const countOf = (f: CollectionFilter) =>
    f === "all" ? tabItems.length : tabItems.filter((item) => collectionStatus(item) === f).length;

  return (
    <div className="min-h-full bg-[#050505] text-[#00ff41] font-mono">
      <div className="sticky top-0 z-40 bg-[#0a0a0a] border-b border-[#00ff41]/30 pt-3 pb-3 px-4 sm:px-6 md:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-lg sm:text-xl font-bold tracking-widest text-[#00f0ff]">
              BLUEPRINT COLLECTION
            </h1>
            <span className="text-xs text-[#00ff41]/40">設計図図鑑</span>
          </div>

          <div className="flex gap-2 mb-3">
            {TABS.map(({ value, label }) => (
              <SciFiButton
                key={value}
                variant={activeTab === value ? "secondary" : "primary"}
                size="sm"
                onClick={() => setActiveTab(value)}
                className="flex-1 sm:flex-none"
              >
                {label}
              </SciFiButton>
            ))}
          </div>

          {collection && (
            <div className="mb-3 space-y-1">
              <ProgressBar label="収集率" progress={collectionProgress(tabItems)} />
              <p className="text-[10px] text-[#00ff41]/40 text-right">
                全体 {formatProgress(collectionProgress(all))}（標準配備を除く）
              </p>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 text-xs border transition-colors ${
                  filter === f
                    ? "border-[#00f0ff] text-[#00f0ff] bg-[#00f0ff]/10"
                    : "border-[#00ff41]/30 text-[#00ff41]/50 hover:border-[#00ff41]/60 hover:text-[#00ff41]/70"
                }`}
              >
                {f === "all" ? "すべて" : COLLECTION_STATUS_LABELS[f]}
                {collection && <span className="ml-1 opacity-70">{countOf(f)}</span>}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 md:px-8 py-4">
        {isError ? (
          <SciFiPanel variant="secondary">
            <div className="p-6">
              <p className="text-[#ffb000] font-bold text-xl mb-2">ERROR: データ取得失敗</p>
              <p className="text-sm">Backendが起動しているか確認してください。</p>
            </div>
          </SciFiPanel>
        ) : isLoading ? (
          <p className="text-center py-16 text-[#ffb000] animate-pulse">LOADING COLLECTION...</p>
        ) : visibleItems.length === 0 ? (
          <p className="text-center py-16 text-sm text-[#00ff41]/50">該当する設計図はありません</p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {visibleItems.map((item) => (
              <BlueprintCollectionCard key={item.blueprint_id} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** 収集率を「所持数 / 対象数（N%）」で返す */
function formatProgress({ owned, total, percent }: CollectionProgress): string {
  return percent === null ? "対象なし" : `${owned} / ${total}（${percent}%）`;
}

/** 収集率のバー */
function ProgressBar({ label, progress }: { label: string; progress: CollectionProgress }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-[#00ff41]/60 tracking-widest">{label}</span>
        <span className="font-bold text-[#00f0ff]">{formatProgress(progress)}</span>
      </div>
      <div
        className="h-2 border border-[#00f0ff]/40 bg-[#0a0a0a]"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress.percent ?? 0}
      >
        <div
          className="h-full bg-[#00f0ff] shadow-[0_0_8px_#00f0ff] transition-all"
          style={{ width: `${progress.percent ?? 0}%` }}
        />
      </div>
    </div>
  );
}
