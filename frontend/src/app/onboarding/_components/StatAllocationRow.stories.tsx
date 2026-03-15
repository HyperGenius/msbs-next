import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import { StatAllocationRow } from "./StatAllocationRow";

const meta: Meta<typeof StatAllocationRow> = {
  title: "Onboarding/StatAllocationRow",
  component: StatAllocationRow,
  parameters: {
    layout: "centered",
  },
  decorators: [
    (Story) => (
      <div className="w-96 bg-[#050505] p-4 font-mono">
        <Story />
      </div>
    ),
  ],
  argTypes: {
    stat: {
      control: "select",
      options: ["DEX", "INT", "REF", "TOU", "LUK"],
    },
    onDecrement: { action: "decremented" },
    onIncrement: { action: "incremented" },
  },
};

export default meta;
type Story = StoryObj<typeof StatAllocationRow>;

/** DEX — ボーナス0（デフォルト） */
export const DEXDefault: Story = {
  args: {
    stat: "DEX",
    description: "器用 (DEX): 命中率・距離減衰緩和・被ダメージカット",
    bonus: 0,
    canDecrement: false,
    canIncrement: true,
    onDecrement: fn(),
    onIncrement: fn(),
  },
};

/** INT — ボーナス割り振り済み */
export const INTWithBonus: Story = {
  args: {
    stat: "INT",
    description: "直感 (INT): クリティカル率・回避率",
    bonus: 3,
    canDecrement: true,
    canIncrement: true,
    onDecrement: fn(),
    onIncrement: fn(),
  },
};

/** REF — ポイント上限到達（インクリメント無効） */
export const REFMaxReached: Story = {
  args: {
    stat: "REF",
    description: "反応 (REF): イニシアチブ・機動性乗算",
    bonus: 2,
    canDecrement: true,
    canIncrement: false,
    onDecrement: fn(),
    onIncrement: fn(),
  },
};

/** TOU */
export const TOU: Story = {
  args: {
    stat: "TOU",
    description: "耐久 (TOU): 攻撃ダメージ加算・被クリティカル率低下",
    bonus: 1,
    canDecrement: true,
    canIncrement: true,
    onDecrement: fn(),
    onIncrement: fn(),
  },
};

/** LUK */
export const LUK: Story = {
  args: {
    stat: "LUK",
    description: "幸運 (LUK): ダメージ乱数偏り・完全回避",
    bonus: 2,
    canDecrement: true,
    canIncrement: false,
    onDecrement: fn(),
    onIncrement: fn(),
  },
};
