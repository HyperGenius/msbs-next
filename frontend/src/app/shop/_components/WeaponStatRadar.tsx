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
import { WEAPON_CHART_CAPS } from "@/utils/weaponChartCaps";

interface WeaponStatRadarProps {
  weapon: Weapon;
}

interface AxisConfig {
  key: keyof typeof WEAPON_CHART_CAPS;
  label: string;
  /** 値が小さいほど高性能な軸（減衰率）は正規化後に反転する */
  invert?: boolean;
}

const AXES: AxisConfig[] = [
  { key: "power", label: "威力" },
  { key: "range", label: "射程" },
  { key: "accuracy", label: "命中率" },
  { key: "optimal_range", label: "最大射程" },
  { key: "decay_rate", label: "減衰率", invert: true },
];

function buildChartData(weapon: Weapon): { subject: string; value: number }[] {
  return AXES.map(({ key, label, invert }) => {
    const raw = (weapon[key] as number | undefined) ?? 0;
    const cap = WEAPON_CHART_CAPS[key];
    const normalized = Math.min(100, Math.round((raw / cap) * 100));
    return {
      subject: label,
      value: invert ? 100 - normalized : normalized,
    };
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
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fill: "#00ff41", fontSize: 9, fontFamily: "monospace" }}
          tickCount={4}
        />
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
