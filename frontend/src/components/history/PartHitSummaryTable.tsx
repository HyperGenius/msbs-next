/* frontend/src/components/history/PartHitSummaryTable.tsx */
"use client";

import { PartHitStat, PartHitSummary } from "@/types/battle";

/** 部位名（hit_part）の表示ラベル */
const PART_LABELS: Record<string, string> = {
  HEAD: "頭部",
  TORSO: "胴体",
  RIGHT_ARM: "右腕",
  LEFT_ARM: "左腕",
  RIGHT_LEG: "右脚",
  LEFT_LEG: "左脚",
};

/** 武器スロット部位ロール（weapon_slot_role）の表示ラベル */
const SLOT_ROLE_LABELS: Record<string, string> = {
  RIGHT_ARM: "右腕武装",
  LEFT_ARM: "左腕武装",
  RACK: "武装ラック",
};

// 表示順（このリストに無いキーはデータにあっても末尾に追加表示する）
const PART_ORDER = ["HEAD", "TORSO", "RIGHT_ARM", "LEFT_ARM", "RIGHT_LEG", "LEFT_LEG"];
const SLOT_ROLE_ORDER = ["RIGHT_ARM", "LEFT_ARM", "RACK"];

/** 表示順リストにあるキーを先頭に、無いキーをそのあとに並べたキー一覧を返す */
function orderedKeys(order: string[], stats: Record<string, PartHitStat>): string[] {
  const known = order.filter((key) => stats[key]);
  const unknown = Object.keys(stats).filter((key) => !order.includes(key));
  return [...known, ...unknown];
}

interface SummarySectionProps {
  title: string;
  order: string[];
  labels: Record<string, string>;
  stats: Record<string, PartHitStat>;
}

function SummarySection({ title, order, labels, stats }: SummarySectionProps) {
  const keys = orderedKeys(order, stats);

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-400 mb-1">{title}</h4>
      {keys.length === 0 ? (
        <p className="text-xs text-gray-500">データがありません</p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500">
              <th className="text-left font-normal py-1">部位</th>
              <th className="text-right font-normal py-1">回数</th>
              <th className="text-right font-normal py-1">ダメージ</th>
            </tr>
          </thead>
          <tbody>
            {keys.map((key) => (
              <tr key={key} className="border-t border-gray-700">
                <td className="py-1 text-gray-200">{labels[key] ?? key}</td>
                <td className="py-1 text-right text-gray-200">{stats[key].hits}</td>
                <td className="py-1 text-right text-gray-200">
                  {stats[key].damage.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

interface PartHitSummaryTableProps {
  summary: PartHitSummary;
}

/**
 * バトル結果の部位別被弾（自機の被弾部位）・命中（自機の武器スロット別命中）を
 * 表形式で表示する (Issue #504)。改造判断（どの部位の装甲を強化すべきか、
 * どの武器スロットが主力かの把握）に使う想定のデータ。
 */
export default function PartHitSummaryTable({ summary }: PartHitSummaryTableProps) {
  const hasData =
    Object.keys(summary.taken).length > 0 || Object.keys(summary.dealt).length > 0;

  if (!hasData) return null;

  return (
    <div className="mt-3 pt-3 border-t border-gray-700 grid grid-cols-1 sm:grid-cols-2 gap-4">
      <SummarySection
        title="被弾部位（自機）"
        order={PART_ORDER}
        labels={PART_LABELS}
        stats={summary.taken}
      />
      <SummarySection
        title="命中武装（自機）"
        order={SLOT_ROLE_ORDER}
        labels={SLOT_ROLE_LABELS}
        stats={summary.dealt}
      />
    </div>
  );
}
