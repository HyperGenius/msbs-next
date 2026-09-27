/* frontend/src/components/loot/LootList.tsx */
import { LootItem } from "@/types/battle";
import LootItemCard from "./LootItemCard";

interface LootListProps {
  /** 戦利品の一覧。空配列はドロップなし、null は導入前のバトル */
  loot: LootItem[] | null | undefined;
  /** 新規入手の演出を再生する */
  animate?: boolean;
}

/**
 * 戦利品の一覧を表示する。ドロップなしは「戦利品なし」を控えめに表示する。
 * 導入前のバトル（null）は何も描画しないため、見出しも呼び出し側で出し分ける。
 */
export default function LootList({ loot, animate = false }: LootListProps) {
  if (loot == null) return null;
  if (loot.length === 0) {
    return <p className="text-xs text-gray-500 font-mono">戦利品なし</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      {loot.map((item) => (
        <LootItemCard key={item.blueprint_id} item={item} animate={animate} />
      ))}
    </div>
  );
}
