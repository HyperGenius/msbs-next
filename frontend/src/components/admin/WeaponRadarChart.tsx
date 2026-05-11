/* frontend/src/components/admin/WeaponRadarChart.tsx */
"use client";

import { MasterWeapon } from "@/types/battle";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface WeaponRadarChartProps {
  selected: MasterWeapon;
  allWeapons: MasterWeapon[];
}

interface AxisConfig {
  key: keyof MasterWeapon["weapon"];
  label: string;
  invert?: boolean;
}

const AXES: AxisConfig[] = [
  { key: "power", label: "威力" },
  { key: "range", label: "射程" },
  { key: "accuracy", label: "命中率" },
  { key: "optimal_range", label: "最適射程" },
  { key: "decay_rate", label: "減衰率", invert: true },
];

function buildChartData(
  selected: MasterWeapon,
  allWeapons: MasterWeapon[]
): { subject: string; selected: number; average: number }[] {
  return AXES.map(({ key, label, invert }) => {
    const rawSelected = (selected.weapon[key] as number) ?? 0;

    // 全武器の最大値で正規化
    const maxVal = Math.max(...allWeapons.map((w) => (w.weapon[key] as number) ?? 0), 1);

    // 全武器平均
    const sum = allWeapons.reduce((acc, w) => acc + ((w.weapon[key] as number) ?? 0), 0);
    const avg = allWeapons.length > 0 ? sum / allWeapons.length : 0;

    // 0-100 に正規化
    const normalize = (v: number) => Math.min(100, Math.round((v / maxVal) * 100));

    // decay_rate は小さいほど高性能なので反転
    const transform = invert
      ? (v: number) => 100 - normalize(v)
      : normalize;

    return {
      subject: label,
      selected: transform(rawSelected),
      average: transform(avg),
    };
  });
}

export default function WeaponRadarChart({
  selected,
  allWeapons,
}: WeaponRadarChartProps) {
  const data = buildChartData(selected, allWeapons);

  return (
    <div className="w-full">
      <p className="text-xs text-[#ffb000]/60 mb-2 text-center">
        バランス比較チャート（全武器最大値で正規化・減衰率は反転表示）
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="65%">
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
            name={selected.name}
            dataKey="selected"
            stroke="#ffb000"
            fill="#ffb000"
            fillOpacity={0.25}
            strokeWidth={2}
          />
          <Radar
            name="全武器平均"
            dataKey="average"
            stroke="#00f0ff"
            fill="#00f0ff"
            fillOpacity={0.12}
            strokeWidth={1.5}
            strokeDasharray="4 2"
          />
          <Legend
            wrapperStyle={{
              fontSize: "11px",
              fontFamily: "monospace",
              color: "#00ff41",
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
