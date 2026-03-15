import type { Meta, StoryObj } from "@storybook/react";
import { ErrorBanner } from "./ErrorBanner";

const meta: Meta<typeof ErrorBanner> = {
  title: "Onboarding/ErrorBanner",
  component: ErrorBanner,
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
};

export default meta;
type Story = StoryObj<typeof ErrorBanner>;

/** エラーメッセージあり */
export const WithMessage: Story = {
  args: {
    message: "パイロット名は2〜15文字で入力してください",
  },
};

/** 勢力未選択エラー */
export const FactionError: Story = {
  args: {
    message: "勢力を選択してください",
  },
};

/** ボーナスポイント未消費エラー */
export const BonusPointsError: Story = {
  args: {
    message: "ボーナスポイントを全て割り振ってください（残り 3 pt）",
  },
};

/** メッセージなし（何も表示しない） */
export const NoMessage: Story = {
  args: {
    message: null,
  },
};
