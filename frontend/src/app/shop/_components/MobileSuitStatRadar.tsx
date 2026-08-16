/** MS購入詳細モーダル用のスペックレーダーチャート（五角形）。単体MSのみ表示し、全MS平均は出力しない */
"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { ShopItemSpecs } from "@/types/shop";
import { MS_CHART_CAPS, APTITUDE_CHART_RANGE } from "@/utils/msChartCaps";

interface MobileSuitStatRadarProps {
  specs: ShopItemSpecs;
  name: string;
}

type CapAxisKey = keyof typeof MS_CHART_CAPS;

interface AxisConfig {
  key: CapAxisKey | "shooting_aptitude" | "melee_aptitude";
  label: string;
}

const AXES: AxisConfig[] = [
  { key: "max_hp", label: "最大耐久" },
  { key: "armor", label: "装甲" },
  { key: "mobility", label: "機動性" },
  { key: "shooting_aptitude", label: "射撃適正" },
  { key: "melee_aptitude", label: "格闘適正" },
];

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

/** 適正値は MIN(0.5)でスコア0・MAX(1.5)でスコア100になるよう線形補間する */
function normalizeAptitude(raw: number): number {
  const { min, max } = APTITUDE_CHART_RANGE;
  const ratio = ((raw - min) / (max - min)) * 100;
  return clampScore(ratio);
}

function normalizeCappedStat(raw: number, cap: number): number {
  return clampScore((raw / cap) * 100);
}

function buildChartData(specs: ShopItemSpecs): { subject: string; value: number }[] {
  return AXES.map(({ key, label }) => {
    if (key === "shooting_aptitude" || key === "melee_aptitude") {
      const raw = specs[key] ?? 1.0;
      return { subject: label, value: normalizeAptitude(raw) };
    }
    const raw = specs[key] ?? 0;
    return { subject: label, value: normalizeCappedStat(raw, MS_CHART_CAPS[key]) };
  });
}

export default function MobileSuitStatRadar({ specs, name }: MobileSuitStatRadarProps) {
  const data = buildChartData(specs);

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
          name={name}
          dataKey="value"
          stroke="#00f0ff"
          fill="#00f0ff"
          fillOpacity={0.25}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
