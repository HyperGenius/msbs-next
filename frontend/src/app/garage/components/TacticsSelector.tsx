/* frontend/src/app/garage/components/TacticsSelector.tsx */
"use client";

import { SciFiSelect } from "@/components/ui";

interface TacticsData {
  priority: "CLOSEST" | "WEAKEST" | "RANDOM" | "STRONGEST" | "THREAT";
  range: "MELEE" | "RANGED" | "BALANCED" | "FLEE";
  // 武装持ち替えポリシー (Issue #506)。バックエンドの tactics dict とキー名を揃える
  weapon_switch_policy: "NEVER" | "RACK_ONLY" | "BALANCED" | "AGGRESSIVE";
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
  { value: "RANGED", label: "RANGED - 射撃距離維持" },
  { value: "BALANCED", label: "BALANCED - バランス型" },
  { value: "FLEE", label: "FLEE - 射程限界から射撃" },
];

// バトルエンジンの挙動（backend/app/engine/engagement_style.py）と一致させる
const RANGE_HELP_TEXTS: Record<TacticsData["range"], string> = {
  MELEE:
    "格闘武器の間合いまで詰めて戦います。互角でも粘り、仕切り直した後はすぐ再突入します。格闘武器が無い機体は射撃の間合いで戦います",
  RANGED:
    "射撃武器の最適距離を保ち、近づかれたら離れます。自分から格闘へ突入せず、互角なら早めに仕切り直します。射撃武器が無い機体は格闘で戦います",
  BALANCED: "そのとき選んだ武器に合わせて、格闘と射撃の間合いを切り替えます",
  FLEE: "射撃武器の射程ぎりぎりを保ち、格闘を避けます。仕切り直した後も距離を取り続けます。射撃武器が無い機体は格闘で戦います",
};

// 武装持ち替えポリシー選択肢 (Issue #506)
const WEAPON_SWITCH_POLICY_OPTIONS = [
  { value: "NEVER", label: "NEVER - 持ち替えない" },
  { value: "RACK_ONLY", label: "RACK_ONLY - 使用不能時のみ強制持ち替え" },
  { value: "BALANCED", label: "BALANCED - おまかせ（期待効果で判断）" },
  { value: "AGGRESSIVE", label: "AGGRESSIVE - 積極的に持ち替える" },
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

      <div className="mb-4">
        <SciFiSelect
          label="交戦距離設定"
          helpText={RANGE_HELP_TEXTS[tactics.range]}
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

      <div>
        <SciFiSelect
          label="武装持ち替えポリシー"
          helpText="複数武装を所持する場合の持ち替え判断方法を設定します"
          variant="accent"
          value={tactics.weapon_switch_policy}
          onChange={(e) =>
            onChange({
              ...tactics,
              weapon_switch_policy: e.target
                .value as TacticsData["weapon_switch_policy"],
            })
          }
          options={WEAPON_SWITCH_POLICY_OPTIONS}
        />
      </div>
    </div>
  );
}
