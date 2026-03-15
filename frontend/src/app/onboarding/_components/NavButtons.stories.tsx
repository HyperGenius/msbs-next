import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import { NavButtons } from "./NavButtons";

const meta: Meta<typeof NavButtons> = {
  title: "Onboarding/NavButtons",
  component: NavButtons,
  parameters: {
    layout: "centered",
  },
  decorators: [
    (Story) => (
      <div className="w-96 bg-[#050505] p-4">
        <Story />
      </div>
    ),
  ],
  argTypes: {
    onBack: { action: "back clicked" },
    onNext: { action: "next clicked" },
    onSubmit: { action: "submit clicked" },
  },
};

export default meta;
type Story = StoryObj<typeof NavButtons>;

/** Step 1: 次へのみ */
export const NextOnly: Story = {
  args: {
    onNext: fn(),
    nextDisabled: false,
  },
};

/** Step 1: 次へ（無効状態） */
export const NextDisabled: Story = {
  args: {
    onNext: fn(),
    nextDisabled: true,
  },
};

/** Step 2 / 3: 戻る + 次へ */
export const BackAndNext: Story = {
  args: {
    onBack: fn(),
    onNext: fn(),
    nextDisabled: false,
  },
};

/** Step 3: 戻る + 送信 */
export const BackAndSubmit: Story = {
  args: {
    onBack: fn(),
    onSubmit: fn(),
    submitDisabled: false,
    submitLabel: "▶ 出撃準備完了 / DEPLOY",
  },
};

/** Step 3: 戻る + 送信（未割り振り — 無効状態） */
export const BackAndSubmitDisabled: Story = {
  args: {
    onBack: fn(),
    onSubmit: fn(),
    submitDisabled: true,
    submitLabel: "▶ 出撃準備完了 / DEPLOY",
  },
};

/** 登録中（ローディング） */
export const Submitting: Story = {
  args: {
    onBack: fn(),
    onSubmit: fn(),
    submitDisabled: true,
    submitLabel: "登録中...",
  },
};
