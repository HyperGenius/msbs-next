/* frontend/src/components/admin/WeaponRadarChart.tsx */
"use client";

import { MasterWeaponEntry } from "@/types/battle";
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
  selected: MasterWeaponEntry;
  allWeapons: MasterWeaponEntry[];
}

interface AxisConfig {
  key: string;
  label: string;
  /** 全武器の最大値で正規化するか (true)、固定最大値を使うか (false) */
  dynamic: boolean;
  /** dynamic=false のときの固定最大値 */
  fixedMax?: number;
  /** 反転表示（小さいほど高性能な軸）*/
  invert?: boolean;
  getter: (w: MasterWeaponEntry) => number;
}

const AXES: AxisConfig[] = [
  {
    key: "power",
    label: "威力",
    dynamic: true,
    getter: (w) => w.weapon.power,
  },
  {
    key: "range",
    label: "射程",
    dynamic: true,
    getter: (w) => w.weapon.range,
  },
  {
    key: "accuracy",
    label: "命中率",
    dynamic: false,
    fixedMax: 100,
    getter: (w) => w.weapon.accuracy,
  },
  {
    key: "optimal_range",
    label: "最適射程",
    dynamic: true,
    getter: (w) => w.weapon.optimal_range ?? 0,
  },
  {
    key: "decay_rate",
    label: "減衰率",
    dynamic: true,
    invert: true,
    getter: (w) => w.weapon.decay_rate ?? 0,
  },
];

function buildChartData(
  selected: MasterWeaponEntry,
  allWeapons: MasterWeaponEntry[]
): { subject: string; selected: number; average: number }[] {
  return AXES.map(({ label, dynamic, fixedMax, invert, getter }) => {
    const rawSelected = getter(selected);
    const sum = allWeapons.reduce((acc, w) => acc + getter(w), 0);
    const avg = allWeapons.length > 0 ? sum / allWeapons.length : 0;

    // 正規化の最大値を決定
    let max: number;
    if (dynamic) {
      max = Math.max(...allWeapons.map(getter), rawSelected, 1);
    } else {
      max = fixedMax ?? 100;
    }

    const normalize = (v: number) => {
      const normalized = Math.min(100, Math.round((v / max) * 100));
      return invert ? 100 - normalized : normalized;
    };

    return {
      subject: label,
      selected: normalize(rawSelected),
      average: normalize(avg),
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
        バランス比較チャート（全武器平均との比較）
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
      <p className="text-xs text-[#00ff41]/30 text-center mt-1">
        ※ 減衰率軸は小さいほど高性能のため表示上反転
      </p>
    </div>
  );
}
