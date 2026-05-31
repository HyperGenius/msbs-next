"use client";

import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";

/** パラメータチューニングパネルで使用するステータスキー（小文字） */
export type StatKey = "sht" | "mel" | "intel" | "ref" | "tou" | "luk";

/** 軸ラベルの表示名（略称） */
const STAT_ABBR: Record<StatKey, string> = {
  sht: "SHT",
  mel: "MEL",
  intel: "INT",
  ref: "REF",
  tou: "TOU",
  luk: "LUK",
};

/** レーダーチャートのデータ形状 */
type RadarDataPoint = {
  stat: string;
  current: number;
  afterPending: number;
};

interface StatusRadarChartProps {
  /** パイロットの現在ステータス値 */
  current: Record<StatKey, number>;
  /** 保留中の加算分（未保存） */
  pending: Record<StatKey, number>;
}

const STAT_ORDER: StatKey[] = ["sht", "mel", "intel", "ref", "tou", "luk"];

/** 最大表示スケール（ランクSの閾値20より大きく設定して余白を持たせる） */
const MAX_VALUE = 25;

/** 軸ラベルのカスタムレンダラー（SF テーマに合わせた amber 色） */
// recharts の tick props は x/y が string | number で渡されるため any を使用
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomAxisLabel(props: any) {
  const { x, y, payload } = props as {
    x: number;
    y: number;
    payload: { value: string };
  };
  return (
    <text
      x={x}
      y={y}
      textAnchor="middle"
      dominantBaseline="central"
      fill="#ffb000"
      fontSize={11}
      fontFamily="monospace"
      fontWeight="bold"
    >
      {payload?.value}
    </text>
  );
}

/**
 * 6ステータスを正六角形レーダーチャートで可視化するコンポーネント。
 * 現在値（緑実線）と保留後予測値（シアン破線）を 2 レイヤーで重ねて表示する。
 */
export default function StatusRadarChart({ current, pending }: StatusRadarChartProps) {
  const data: RadarDataPoint[] = STAT_ORDER.map((stat) => ({
    stat: STAT_ABBR[stat],
    current: current[stat] ?? 0,
    afterPending: (current[stat] ?? 0) + (pending[stat] ?? 0),
  }));

  const hasPending = STAT_ORDER.some((s) => (pending[s] ?? 0) > 0);

  return (
    <div className="w-full h-full min-h-[200px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 16, right: 24, bottom: 16, left: 24 }}>
          {/* グリッド線: SF テーマに合わせた暗い amber */}
          <PolarGrid stroke="#ffb000" strokeOpacity={0.2} />

          {/* 軸ラベル */}
          <PolarAngleAxis
            dataKey="stat"
            tick={(props) => <CustomAxisLabel {...props} />}
          />

          {/* 現在値レイヤー（緑塗りつぶし・実線） */}
          <Radar
            name="現在値"
            dataKey="current"
            stroke="#00ff41"
            strokeWidth={1.5}
            fill="#00ff41"
            fillOpacity={0.25}
            dot={false}
            isAnimationActive={false}
          />

          {/* 保留後予測値レイヤー（シアン破線・塗りなし）: 保留がある場合のみ表示 */}
          {hasPending && (
            <Radar
              name="保留後"
              dataKey="afterPending"
              stroke="#00f0ff"
              strokeWidth={1.5}
              strokeDasharray="4 2"
              fill="#00f0ff"
              fillOpacity={0.1}
              dot={false}
              isAnimationActive={false}
            />
          )}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
