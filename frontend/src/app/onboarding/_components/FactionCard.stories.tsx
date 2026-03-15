import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import { FactionCard } from "./FactionCard";

const meta: Meta<typeof FactionCard> = {
  title: "Onboarding/FactionCard",
  component: FactionCard,
  parameters: {
    layout: "centered",
  },
  decorators: [
    (Story) => (
      <div className="w-64 bg-[#050505] p-4 font-mono">
        <Story />
      </div>
    ),
  ],
  argTypes: {
    onSelect: { action: "faction selected" },
  },
};

export default meta;
type Story = StoryObj<typeof FactionCard>;

/** 地球連邦軍 — 未選択 */
export const FederationUnselected: Story = {
  args: {
    faction: "FEDERATION",
    label: "地球連邦軍",
    subLabel: "Earth Federation Forces",
    mobilesuit: "RGM-79T GM Trainer",
    isSelected: false,
    onSelect: fn(),
  },
};

/** 地球連邦軍 — 選択済み */
export const FederationSelected: Story = {
  args: {
    faction: "FEDERATION",
    label: "地球連邦軍",
    subLabel: "Earth Federation Forces",
    mobilesuit: "RGM-79T GM Trainer",
    isSelected: true,
    onSelect: fn(),
  },
};

/** ジオン公国軍 — 未選択 */
export const ZeonUnselected: Story = {
  args: {
    faction: "ZEON",
    label: "ジオン公国軍",
    subLabel: "Principality of Zeon",
    mobilesuit: "MS-06T Zaku II Trainer",
    isSelected: false,
    onSelect: fn(),
  },
};

/** ジオン公国軍 — 選択済み */
export const ZeonSelected: Story = {
  args: {
    faction: "ZEON",
    label: "ジオン公国軍",
    subLabel: "Principality of Zeon",
    mobilesuit: "MS-06T Zaku II Trainer",
    isSelected: true,
    onSelect: fn(),
  },
};
