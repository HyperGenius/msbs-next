import type { Meta, StoryObj } from "@storybook/react";
import { StepIndicator } from "./StepIndicator";

const meta: Meta<typeof StepIndicator> = {
  title: "Onboarding/StepIndicator",
  component: StepIndicator,
  parameters: {
    layout: "centered",
  },
  argTypes: {
    currentStep: {
      control: { type: "select" },
      options: [1, 2, 3],
    },
    totalSteps: {
      control: { type: "number", min: 1, max: 5 },
    },
  },
};

export default meta;
type Story = StoryObj<typeof StepIndicator>;

/** Step 1 — 最初のステップ */
export const Step1: Story = {
  args: { currentStep: 1 },
};

/** Step 2 — 2番目のステップ */
export const Step2: Story = {
  args: { currentStep: 2 },
};

/** Step 3 — 最終ステップ（全バー点灯） */
export const Step3Complete: Story = {
  args: { currentStep: 3 },
};
