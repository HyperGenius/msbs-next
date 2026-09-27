import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import TechnologyProgressCard from "./TechnologyProgressCard";
import { PlayerTechnologyProgress } from "@/types/battle";

const meta: Meta<typeof TechnologyProgressCard> = {
  title: "Collection/TechnologyProgressCard",
  component: TechnologyProgressCard,
  parameters: {
    backgrounds: { default: "dark" },
  },
  decorators: [
    (Story) => (
      <div className="max-w-md p-4 bg-[#0a0a0a]">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof TechnologyProgressCard>;

const psycommu: PlayerTechnologyProgress = {
  tech_id: "psycommu_tech",
  name: "サイコミュ技術",
  description: "サイコミュ武器、サイコミュ搭載機体の開発に必要な技術",
  level: 1,
  max_level: 3,
  fragment_count: 5,
  next_level_threshold: 8,
  fragments_to_next_level: 3,
  overflow_credit_value: 500,
  obtainable_theaters: [{ label: "全戦域", requires_win: false }],
};

/** 未入手（Lv0） */
export const NotStarted: Story = {
  args: {
    technology: {
      ...psycommu,
      level: 0,
      fragment_count: 0,
      next_level_threshold: 3,
      fragments_to_next_level: 3,
    },
  },
};

/** 途中のLv */
export const InProgress: Story = {
  args: { technology: psycommu },
};

/** 最大Lv（以降の断片は換金） */
export const MaxLevel: Story = {
  args: {
    technology: {
      ...psycommu,
      level: 3,
      fragment_count: 15,
      next_level_threshold: null,
      fragments_to_next_level: null,
    },
  },
};

/** 勝利時のみドロップ */
export const WinOnly: Story = {
  args: {
    technology: {
      ...psycommu,
      obtainable_theaters: [{ label: "全戦域", requires_win: true }],
    },
  },
};

/** 入手先が無い */
export const Unavailable: Story = {
  args: { technology: { ...psycommu, obtainable_theaters: [] } },
};
