import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import { BackgroundCard } from "./BackgroundCard";
import type { Background } from "../_types";

const ACADEMY_ELITE: Background = {
  id: "ACADEMY_ELITE",
  name: "士官学校卒 (Academy Elite)",
  description: "正規の軍事教育を受けたエリート。高度な戦術理解とバランスの取れた能力を持つ。",
  baseStats: { SHT: 10, MEL: 10, INT: 8, REF: 12, TOU: 10, LUK: 5 },
};

const STREET_SURVIVOR: Background = {
  id: "STREET_SURVIVOR",
  name: "現場叩き上げ (Street Survivor)",
  description: "過酷な環境を生き抜いてきた叩き上げ。野性の勘と並外れた反射神経を誇る。",
  baseStats: { SHT: 7, MEL: 7, INT: 12, REF: 7, TOU: 14, LUK: 8 },
};

const EX_MECHANIC: Background = {
  id: "EX_MECHANIC",
  name: "元メカニック (Ex-Mechanic)",
  description: "機械の構造を知り尽くした技術者出身。機体の挙動を正確に制御する器用さを持つ。",
  baseStats: { SHT: 14, MEL: 14, INT: 8, REF: 6, TOU: 12, LUK: 3 },
};

const meta: Meta<typeof BackgroundCard> = {
  title: "Onboarding/BackgroundCard",
  component: BackgroundCard,
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
    onSelect: { action: "background selected" },
  },
};

export default meta;
type Story = StoryObj<typeof BackgroundCard>;

/** 士官学校卒 — 未選択 */
export const AcademyEliteUnselected: Story = {
  args: {
    background: ACADEMY_ELITE,
    isSelected: false,
    onSelect: fn(),
  },
};

/** 士官学校卒 — 選択済み */
export const AcademyEliteSelected: Story = {
  args: {
    background: ACADEMY_ELITE,
    isSelected: true,
    onSelect: fn(),
  },
};

/** 現場叩き上げ — 未選択 */
export const StreetSurvivorUnselected: Story = {
  args: {
    background: STREET_SURVIVOR,
    isSelected: false,
    onSelect: fn(),
  },
};

/** 現場叩き上げ — 選択済み */
export const StreetSurvivorSelected: Story = {
  args: {
    background: STREET_SURVIVOR,
    isSelected: true,
    onSelect: fn(),
  },
};

/** 元メカニック — 未選択 */
export const ExMechanicUnselected: Story = {
  args: {
    background: EX_MECHANIC,
    isSelected: false,
    onSelect: fn(),
  },
};

/** 元メカニック — 選択済み */
export const ExMechanicSelected: Story = {
  args: {
    background: EX_MECHANIC,
    isSelected: true,
    onSelect: fn(),
  },
};
