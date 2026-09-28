import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import TheaterForecastCard from "./TheaterForecastCard";
import { MobileSuit, TheaterForecast } from "@/types/battle";

const meta: Meta<typeof TheaterForecastCard> = {
  title: "Dashboard/TheaterForecastCard",
  component: TheaterForecastCard,
  parameters: {
    layout: "padded",
    backgrounds: { default: "dark" },
  },
  decorators: [
    (Story) => (
      <div className="max-w-md bg-[#050505] p-4">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof TheaterForecastCard>;

// ── サンプルデータ ──────────────────────────────────────────

const solomon: Omit<TheaterForecast, "scheduled_at" | "is_current"> = {
  theater_id: "solomon",
  theater_name: "ソロモン宙域",
  environment_id: "SPACE",
  environment_name: "宇宙",
  default_terrain_grade: "A",
  minovsky_density: 0.28,
  minovsky_level: "LOW",
  hint: "ビーム・高機動・長距離に強い機体が有利",
  description: "ジオン公国軍の宇宙要塞ソロモン周辺の宙域。",
};

const jungle: Omit<TheaterForecast, "scheduled_at" | "is_current"> = {
  theater_id: "southeast_asia_jungle",
  theater_name: "東南アジア密林",
  environment_id: "FOREST",
  environment_name: "森林",
  default_terrain_grade: "A",
  minovsky_density: 0.62,
  minovsky_level: "MEDIUM",
  hint: "格闘・索敵に強い機体が有利。長距離射撃は不利",
  description: "視界の悪い密林地帯。",
};

const spaceForecasts: TheaterForecast[] = [
  { ...solomon, scheduled_at: "2026-10-01T12:00:00Z", is_current: true },
  { ...jungle, scheduled_at: "2026-10-02T12:00:00Z", is_current: false },
  {
    ...solomon,
    minovsky_density: 0.45,
    minovsky_level: "MEDIUM",
    scheduled_at: "2026-10-03T12:00:00Z",
    is_current: false,
  },
];

const forestForecasts: TheaterForecast[] = [
  {
    ...jungle,
    minovsky_density: 0.71,
    minovsky_level: "HIGH",
    scheduled_at: "2026-10-02T12:00:00Z",
    is_current: true,
  },
  { ...solomon, scheduled_at: "2026-10-03T12:00:00Z", is_current: false },
  { ...jungle, scheduled_at: "2026-10-04T12:00:00Z", is_current: false },
];

const gundam: MobileSuit = {
  id: "ms-001",
  name: "RX-78-2 ガンダム",
  max_hp: 1200,
  current_hp: 1200,
  armor: 70,
  mobility: 1.6,
  position: { x: 0, y: 0, z: 0 },
  side: "PLAYER",
  tactics: { priority: "CLOSEST", range: "BALANCED" },
  weapons: [],
  terrain_adaptability: { SPACE: "A", GROUND: "A", FOREST: "B" },
};

const zakuSpaceOnly: MobileSuit = {
  ...gundam,
  id: "ms-002",
  name: "MS-06R ザクII 高機動型",
  terrain_adaptability: { SPACE: "S", FOREST: "D" },
};

// ── ストーリー ──────────────────────────────────────────────

/** 宇宙の戦域（未エントリー: 機体の地形適正は出さない） */
export const Space: Story = {
  args: { forecasts: spaceForecasts },
};

/** 森林の戦域（エントリー中の機体の地形適正 B） */
export const Forest: Story = {
  args: { forecasts: forestForecasts, mobileSuit: gundam },
};

/** 不向きな機体（地形適正 C 以下で注意表示） */
export const UnsuitableMobileSuit: Story = {
  args: { forecasts: forestForecasts, mobileSuit: zakuSpaceOnly },
};

/** 予報なし（有効な戦域が無い） */
export const NoForecast: Story = {
  args: { forecasts: [] },
};

/** 未知の環境タイプ（既定のアイコンと色） */
export const UnknownEnvironment: Story = {
  args: {
    forecasts: [
      {
        ...solomon,
        theater_id: "odessa",
        theater_name: "オデッサ",
        environment_id: "DESERT",
        environment_name: "砂漠",
        scheduled_at: "2026-10-01T12:00:00Z",
        is_current: true,
      },
    ],
    mobileSuit: gundam,
  },
};
