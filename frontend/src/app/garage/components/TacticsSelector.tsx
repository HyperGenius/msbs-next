/* frontend/src/app/garage/components/TacticsSelector.tsx */
"use client";

import { SciFiSelect } from "@/components/ui";

interface TacticsData {
  priority: "CLOSEST" | "WEAKEST" | "RANDOM" | "STRONGEST" | "THREAT";
  range: "MELEE" | "RANGED" | "BALANCED" | "FLEE";
}

interface TacticsSelectorProps {
  tactics: TacticsData;
  onChange: (tactics: TacticsData) => void;
}

const PRIORITY_OPTIONS = [
  { value: "CLOSEST", label: "CLOSEST - 最寄りの敵" },
  { value: "WEAKEST", label: "WEAKEST - HP最小の敵" },
  { value: "STRONGEST", label: "STRONGEST - 強敵優先 (戦略価値)" },
  { value: "THREAT", label: "THREAT - 脅威度優先" },
  { value: "RANDOM", label: "RANDOM - ランダム選択" },
];

const RANGE_OPTIONS = [
  { value: "MELEE", label: "MELEE - 近接突撃" },
  { value: "RANGED", label: "RANGED - 遠距離維持" },
  { value: "BALANCED", label: "BALANCED - バランス型" },
  { value: "FLEE", label: "FLEE - 回避優先" },
];

export default function TacticsSelector({
  tactics,
  onChange,
}: TacticsSelectorProps) {
  return (
    <div className="pt-4 border-t border-green-800">
      <h3 className="text-lg font-bold mb-4 text-green-300">
        戦術設定 (Tactics)
      </h3>

      <div className="mb-4">
        <SciFiSelect
          label="ターゲット優先度"
          helpText="攻撃対象の選択方法を設定します"
          variant="accent"
          value={tactics.priority}
          onChange={(e) =>
            onChange({
              ...tactics,
              priority: e.target.value as TacticsData["priority"],
            })
          }
          options={PRIORITY_OPTIONS}
        />
      </div>

      <div>
        <SciFiSelect
          label="交戦距離設定"
          helpText="戦闘時の移動パターンを設定します"
          variant="accent"
          value={tactics.range}
          onChange={(e) =>
            onChange({
              ...tactics,
              range: e.target.value as TacticsData["range"],
            })
          }
          options={RANGE_OPTIONS}
        />
      </div>
    </div>
  );
}
