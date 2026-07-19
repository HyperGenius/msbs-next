/* admin-tool/src/components/admin/CombatSimulationPanel.tsx */
"use client";

import { useMemo, useState } from "react";
import { useCombatSimulation } from "@/hooks/useCombatSimulation";
import {
  AttackSector,
  DEFAULT_PILOT_STATS,
  MasterMobileSuit,
  PilotStatsInput,
} from "@/types/admin";
import { SciFiButton, SciFiHeading } from "@/components/ui";

interface CombatSimulationPanelProps {
  /** 攻撃側（現在編集中の機体） */
  attacker: MasterMobileSuit;
  /** 選択可能な全機体（防御側の選択肢） */
  allSuits: MasterMobileSuit[];
}

const SECTOR_OPTIONS: { value: AttackSector; label: string }[] = [
  { value: "FRONT", label: "正面 (FRONT)" },
  { value: "FRONT_SIDE", label: "側面前方 (FRONT_SIDE)" },
  { value: "REAR_SIDE", label: "側面後方 (REAR_SIDE)" },
  { value: "REAR", label: "背面 (REAR)" },
];

const PILOT_STAT_FIELDS: { key: keyof PilotStatsInput; label: string }[] = [
  { key: "sht", label: "射撃" },
  { key: "mel", label: "格闘" },
  { key: "intel", label: "直感" },
  { key: "ref", label: "反応" },
  { key: "tou", label: "耐久" },
  { key: "luk", label: "幸運" },
];

function PilotStatsInputRow({
  values,
  onChange,
}: {
  values: PilotStatsInput;
  onChange: (values: PilotStatsInput) => void;
}) {
  return (
    <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
      {PILOT_STAT_FIELDS.map(({ key, label }) => (
        <label key={String(key)} className="text-xs text-[#00ff41]/70">
          {label}
          <input
            type="number"
            value={values[key]}
            onChange={(e) =>
              onChange({ ...values, [key]: Number(e.target.value) || 0 })
            }
            className="mt-1 w-full bg-black border border-[#00ff41]/30 text-[#00ff41] px-1.5 py-1 text-sm font-mono focus:border-[#00ff41] focus:outline-none"
          />
        </label>
      ))}
    </div>
  );
}

function StatDisplay({ label, value, unit = "" }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="border border-[#00ff41]/20 px-3 py-2">
      <div className="text-[10px] text-[#00ff41]/50 uppercase">{label}</div>
      <div className="text-lg font-bold text-[#00ff41]">
        {value}
        {unit}
      </div>
    </div>
  );
}

export default function CombatSimulationPanel({ attacker, allSuits }: CombatSimulationPanelProps) {
  const { result, isLoading, error, simulate } = useCombatSimulation();

  const defenderCandidates = allSuits;
  const [defenderId, setDefenderId] = useState<string>(
    defenderCandidates.find((ms) => ms.id !== attacker.id)?.id ?? attacker.id
  );
  const defender = useMemo(
    () => defenderCandidates.find((ms) => ms.id === defenderId) ?? attacker,
    [defenderCandidates, defenderId, attacker]
  );

  const [weaponId, setWeaponId] = useState<string>(attacker.specs.weapons[0]?.id ?? "");
  const weapon = attacker.specs.weapons.find((w) => w.id === weaponId) ?? attacker.specs.weapons[0];

  const [attackerPilot, setAttackerPilot] = useState<PilotStatsInput>(DEFAULT_PILOT_STATS);
  const [defenderPilot, setDefenderPilot] = useState<PilotStatsInput>(DEFAULT_PILOT_STATS);
  const [distance, setDistance] = useState<number>(weapon?.optimal_range ?? 300);
  const [attackSector, setAttackSector] = useState<AttackSector>("FRONT_SIDE");
  const [trials, setTrials] = useState<number>(1000);

  if (!weapon) {
    return (
      <div className="p-4 text-sm text-[#00ff41]/40">
        武装が設定されていないためシミュレーションできません。
      </div>
    );
  }

  async function handleRun(withMonteCarlo: boolean) {
    await simulate({
      attacker_spec: attacker.specs,
      attacker_weapon_id: weapon.id,
      attacker_pilot: attackerPilot,
      defender_spec: defender.specs,
      defender_pilot: defenderPilot,
      distance,
      attack_sector: attackSector,
      trials: withMonteCarlo ? trials : undefined,
    });
  }

  return (
    <div className="space-y-4">
      {/* 攻撃側 */}
      <div>
        <SciFiHeading level={4} className="mb-2 text-sm">
          攻撃側: {attacker.name}
        </SciFiHeading>
        <label className="text-xs text-[#00ff41]/70 block mb-2">
          使用武装
          <select
            value={weaponId || weapon.id}
            onChange={(e) => setWeaponId(e.target.value)}
            className="mt-1 w-full bg-black border border-[#00ff41]/30 text-[#00ff41] px-2 py-1.5 text-sm font-mono focus:border-[#00ff41] focus:outline-none"
          >
            {attacker.specs.weapons.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} (攻撃力: {w.power} / 命中率: {w.accuracy}%)
              </option>
            ))}
          </select>
        </label>
        <PilotStatsInputRow values={attackerPilot} onChange={setAttackerPilot} />
      </div>

      {/* 防御側 */}
      <div>
        <SciFiHeading level={4} className="mb-2 text-sm">
          防御側
        </SciFiHeading>
        <label className="text-xs text-[#00ff41]/70 block mb-2">
          対象機体
          <select
            value={defenderId}
            onChange={(e) => setDefenderId(e.target.value)}
            className="mt-1 w-full bg-black border border-[#00ff41]/30 text-[#00ff41] px-2 py-1.5 text-sm font-mono focus:border-[#00ff41] focus:outline-none"
          >
            {defenderCandidates.map((ms) => (
              <option key={ms.id} value={ms.id}>
                {ms.name} (装甲: {ms.specs.armor} / 機動: {ms.specs.mobility})
              </option>
            ))}
          </select>
        </label>
        <PilotStatsInputRow values={defenderPilot} onChange={setDefenderPilot} />
      </div>

      {/* 距離・セクタ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="text-xs text-[#00ff41]/70">
          距離 (m) — 最適射程: {weapon.optimal_range}m / 射程: {weapon.range}m
          <input
            type="range"
            min={0}
            max={weapon.range}
            step={10}
            value={distance}
            onChange={(e) => setDistance(Number(e.target.value))}
            className="mt-1 w-full"
          />
          <div className="text-right text-[#00ff41] text-sm">{distance}m</div>
        </label>
        <label className="text-xs text-[#00ff41]/70">
          攻撃セクタ
          <select
            value={attackSector}
            onChange={(e) => setAttackSector(e.target.value as AttackSector)}
            className="mt-1 w-full bg-black border border-[#00ff41]/30 text-[#00ff41] px-2 py-1.5 text-sm font-mono focus:border-[#00ff41] focus:outline-none"
          >
            {SECTOR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* 実行ボタン */}
      <div className="flex flex-wrap gap-2">
        <SciFiButton variant="primary" size="sm" disabled={isLoading} onClick={() => handleRun(false)}>
          理論値を計算
        </SciFiButton>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={1}
            max={5000}
            value={trials}
            onChange={(e) => setTrials(Number(e.target.value) || 1)}
            className="w-24 bg-black border border-[#ffb000]/30 text-[#ffb000] px-2 py-1.5 text-sm font-mono focus:border-[#ffb000] focus:outline-none"
          />
          <SciFiButton variant="secondary" size="sm" disabled={isLoading} onClick={() => handleRun(true)}>
            N回試行
          </SciFiButton>
        </div>
      </div>

      {isLoading && <p className="text-[#ffb000] animate-pulse text-sm">計算中...</p>}
      {error && <p className="text-red-400 text-sm">{error.message}</p>}

      {/* 結果表示 */}
      {result && (
        <div className="space-y-3 pt-2 border-t border-[#00ff41]/20">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <StatDisplay label="命中率(理論値)" value={result.hit_chance.toFixed(1)} unit="%" />
            <StatDisplay label="クリティカル率(理論値)" value={result.crit_chance.toFixed(1)} unit="%" />
            <StatDisplay label="ダメージ(非クリ)" value={result.resistance_applied_damage} />
            <StatDisplay label="ダメージ(クリティカル)" value={result.crit_damage} />
          </div>

          {result.monte_carlo && (
            <div>
              <SciFiHeading level={4} className="mb-2 text-sm">
                モンテカルロ試行結果（{result.monte_carlo.trials}回）
              </SciFiHeading>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <StatDisplay label="実測命中率" value={result.monte_carlo.actual_hit_rate.toFixed(1)} unit="%" />
                <StatDisplay label="実測クリティカル率" value={result.monte_carlo.actual_crit_rate.toFixed(1)} unit="%" />
                <StatDisplay label="平均ダメージ" value={result.monte_carlo.avg_damage.toFixed(1)} />
                <StatDisplay
                  label="ダメージ幅"
                  value={`${result.monte_carlo.min_damage}〜${result.monte_carlo.max_damage}`}
                />
              </div>
              {result.monte_carlo.perfect_evade_rate > 0 && (
                <p className="text-xs text-[#00f0ff] mt-2">
                  完全回避発生率: {result.monte_carlo.perfect_evade_rate.toFixed(2)}%
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
