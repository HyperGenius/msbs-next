/** 武器詳細モーダル用のスペックレーダーチャート（五角形）。単体武器のみ表示し、全武器平均は出力しない */
"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { Weapon } from "@/types/weapon";
import { WEAPON_CHART_CAPS, DECAY_RATE_CHART_RANGE } from "@/utils/weaponChartCaps";

interface WeaponStatRadarProps {
  weapon: Weapon;
}

type CapAxisKey = keyof typeof WEAPON_CHART_CAPS;

interface AxisConfig {
  key: CapAxisKey | "decay_rate";
  label: string;
}

const AXES: AxisConfig[] = [
  { key: "power", label: "威力" },
  { key: "range", label: "射程" },
  { key: "accuracy", label: "命中率" },
  { key: "optimal_range", label: "最適射程" },
  { key: "decay_rate", label: "減衰率" },
];

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

/** 減衰率は best(0.01)で100・worst(0.25)で0 になるよう線形補間する */
function normalizeDecayRate(raw: number): number {
  const { best, worst } = DECAY_RATE_CHART_RANGE;
  const ratio = ((worst - raw) / (worst - best)) * 100;
  return clampScore(ratio);
}

function normalizeCappedStat(raw: number, cap: number): number {
  return clampScore((raw / cap) * 100);
}

function buildChartData(weapon: Weapon): { subject: string; value: number }[] {
  return AXES.map(({ key, label }) => {
    const raw = (weapon[key] as number | undefined) ?? 0;
    const value =
      key === "decay_rate"
        ? normalizeDecayRate(raw)
        : normalizeCappedStat(raw, WEAPON_CHART_CAPS[key]);
    return { subject: label, value };
  });
}

export default function WeaponStatRadar({ weapon }: WeaponStatRadarProps) {
  const data = buildChartData(weapon);

  return (
    <ResponsiveContainer width="100%" height={240}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="#00ff41" strokeOpacity={0.2} />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: "#00ff41", fontSize: 11, fontFamily: "monospace" }}
        />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} tickCount={4} />
        <Radar
          name={weapon.name}
          dataKey="value"
          stroke="#ffb000"
          fill="#ffb000"
          fillOpacity={0.25}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
