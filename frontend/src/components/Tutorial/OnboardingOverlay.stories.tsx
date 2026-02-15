import type { Meta, StoryObj } from '@storybook/react';
import OnboardingOverlay from './OnboardingOverlay';

const meta: Meta<typeof OnboardingOverlay> = {
  title: 'Tutorial/OnboardingOverlay',
  component: OnboardingOverlay,
  parameters: { layout: 'fullscreen' },
  decorators: [
    (Story) => (
      <div className="relative min-h-screen bg-gray-900 p-8">
        {/* targetSelectorで指定されるダミー要素 */}
        <button id="target-btn" className="bg-green-600 text-white px-4 py-2">
          Target Button
        </button>
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof OnboardingOverlay>;

export const Default: Story = {
  args: {
    show: true,
    // ...必要なprops
  },
};

