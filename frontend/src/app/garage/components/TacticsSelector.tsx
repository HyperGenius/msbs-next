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
  { value: "CLOSEST", label: "CLOSEST - 最寄りの敵", description: "最も近い敵を狙います" },
  { value: "WEAKEST", label: "WEAKEST - HP最小の敵", description: "残りHPが最も少ない敵を狙い、撃破を優先します" },
  { value: "STRONGEST", label: "STRONGEST - 強敵優先 (戦略価値)", description: "戦略価値の高い敵を優先して狙います" },
  { value: "THREAT", label: "THREAT - 脅威度優先", description: "こちらへの脅威が最も大きい敵を狙います" },
  { value: "RANDOM", label: "RANDOM - ランダム選択", description: "狙う敵を無作為に選びます" },
];

// バトルエンジンの挙動（backend/app/engine/engagement_style.py）と一致させる
const RANGE_OPTIONS = [
  {
    value: "MELEE",
    label: "MELEE - 近接突撃",
    description:
      "格闘武器の間合いまで詰めて戦います。互角でも粘り、仕切り直した後はすぐ再突入します。格闘武器が無い機体は射撃の間合いで戦います",
  },
  {
    value: "RANGED",
    label: "RANGED - 射撃距離維持",
    description:
      "射撃武器の最適距離を保ち、近づかれたら離れます。自分から格闘へ突入せず、互角なら早めに仕切り直します。射撃武器が無い機体は格闘で戦います",
  },
  {
    value: "BALANCED",
    label: "BALANCED - バランス型",
    description: "そのとき選んだ武器に合わせて、格闘と射撃の間合いを切り替えます",
  },
  {
    value: "FLEE",
    label: "FLEE - 射程限界から射撃",
    description:
      "射撃武器の射程ぎりぎりを保ち、格闘を避けます。仕切り直した後も距離を取り続けます。射撃武器が無い機体は格闘で戦います",
  },
];

const WEAPON_SWITCH_POLICY_OPTIONS = [
  { value: "NEVER", label: "NEVER - 持ち替えない", description: "状況に関わらず手持ちの武器を使い続けます" },
  { value: "RACK_ONLY", label: "RACK_ONLY - 使用不能時のみ強制持ち替え", description: "弾切れやクールタイム中になったときだけ持ち替えます" },
  { value: "BALANCED", label: "BALANCED - おまかせ（期待効果で判断）", description: "持ち替えの効果が隙のコストに見合うときだけ持ち替えます" },
  { value: "AGGRESSIVE", label: "AGGRESSIVE - 積極的に持ち替える", description: "隙のコストを気にせず、より適した武装があれば毎回持ち替えます" },
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
          onChange={(v) =>
            onChange({
              ...tactics,
              priority: v as TacticsData["priority"],
            })
          }
          options={PRIORITY_OPTIONS}
        />
      </div>

      <div className="mb-4">
        <SciFiSelect
          label="交戦距離設定"
          variant="accent"
          value={tactics.range}
          onChange={(v) =>
            onChange({
              ...tactics,
              range: v as TacticsData["range"],
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
          onChange={(v) =>
            onChange({
              ...tactics,
              weapon_switch_policy: v as TacticsData["weapon_switch_policy"],
            })
          }
          options={WEAPON_SWITCH_POLICY_OPTIONS}
        />
      </div>
    </div>
  );
}
