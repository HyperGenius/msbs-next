import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, within } from "storybook/test";
import SciFiSelect from "./SciFiSelect";

const meta: Meta<typeof SciFiSelect> = {
  title: "UI/SciFiSelect",
  component: SciFiSelect,
  parameters: { layout: "padded", backgrounds: { default: "dark" } },
  decorators: [
    (Story) => (
      <div className="max-w-sm bg-[#050505] p-4 min-h-80">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof SciFiSelect>;

const TACTIC_OPTIONS = [
  { value: "MELEE", label: "MELEE - 近接突撃", description: "格闘武器の間合いまで詰めて戦います" },
  { value: "RANGED", label: "RANGED - 射撃距離維持", description: "射撃武器の最適距離を保ちます" },
  { value: "BALANCED", label: "BALANCED - バランス型", description: "状況に合わせて間合いを切り替えます" },
];

function Controlled({
  initial = "MELEE",
  ...props
}: Partial<React.ComponentProps<typeof SciFiSelect>> & { initial?: string }) {
  const [value, setValue] = useState(initial);
  return (
    <SciFiSelect
      label="交戦距離設定"
      variant="accent"
      options={TACTIC_OPTIONS}
      {...props}
      value={value}
      onChange={setValue}
    />
  );
}

export const WithDescriptions: Story = {
  render: () => <Controlled />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const trigger = canvas.getByRole("combobox", { name: "交戦距離設定" });
    await userEvent.click(trigger);
    await expect(canvas.getByRole("listbox")).toBeVisible();
    await userEvent.click(canvas.getByRole("option", { name: /RANGED/ }));
    await expect(canvas.queryByRole("listbox")).toBeNull();
    await expect(trigger).toHaveTextContent("RANGED - 射撃距離維持");
  },
};

export const KeyboardOperation: Story = {
  render: () => <Controlled />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const trigger = canvas.getByRole("combobox");
    trigger.focus();
    await userEvent.keyboard("{ArrowDown}{ArrowDown}{Enter}");
    await expect(trigger).toHaveTextContent("RANGED");
    await userEvent.keyboard("{ArrowDown}{Escape}");
    await expect(canvas.queryByRole("listbox")).toBeNull();
    await expect(trigger).toHaveTextContent("RANGED");
  },
};

export const Disabled: Story = {
  render: () => <Controlled disabled />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("combobox"), { pointerEventsCheck: 0 });
    await expect(canvas.queryByRole("listbox")).toBeNull();
  },
};

export const LongList: Story = {
  render: () => (
    <Controlled
      initial="ms0"
      label="装備先の機体"
      variant="primary"
      options={Array.from({ length: 20 }, (_, i) => ({ value: `ms${i}`, label: `ザク II #${i + 1}` }))}
    />
  ),
};
