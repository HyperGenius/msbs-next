/* frontend/src/components/admin/MobileSuitRadarChart.tsx */
"use client";

import { MasterMobileSuit } from "@/types/battle";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface MobileSuitRadarChartProps {
  selected: MasterMobileSuit;
  allSuits: MasterMobileSuit[];
}

interface AxisConfig {
  key: keyof MasterMobileSuit["specs"];
  label: string;
  max: number;
}

const AXES: AxisConfig[] = [
  { key: "max_hp", label: "HP", max: 2000 },
  { key: "armor", label: "装甲", max: 200 },
  { key: "mobility", label: "機動性", max: 3.0 },
  { key: "shooting_aptitude", label: "射撃適性", max: 2.0 },
  { key: "melee_aptitude", label: "格闘適性", max: 2.0 },
];

function buildChartData(
  selected: MasterMobileSuit,
  allSuits: MasterMobileSuit[]
): { subject: string; selected: number; average: number }[] {
  return AXES.map(({ key, label, max }) => {
    const rawSelected = selected.specs[key] as number;
    // 全機体平均
    const sum = allSuits.reduce((acc, ms) => acc + (ms.specs[key] as number), 0);
    const avg = allSuits.length > 0 ? sum / allSuits.length : 0;

    // 0-100 に正規化
    const normalize = (v: number) => Math.min(100, Math.round((v / max) * 100));

    return {
      subject: label,
      selected: normalize(rawSelected),
      average: normalize(avg),
    };
  });
}

export default function MobileSuitRadarChart({
  selected,
  allSuits,
}: MobileSuitRadarChartProps) {
  const data = buildChartData(selected, allSuits);

  return (
    <div className="w-full">
      <p className="text-xs text-[#ffb000]/60 mb-2 text-center">
        バランス比較チャート（全機体平均との比較）
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
            name="全機体平均"
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
