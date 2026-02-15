import type { Meta, StoryObj } from '@storybook/react';
import OnboardingOverlay from './OnboardingOverlay';

const meta: Meta<typeof OnboardingOverlay> = {
  title: 'Tutorial/OnboardingOverlay',
  component: OnboardingOverlay,
  parameters: { layout: 'fullscreen' },
  decorators: [
    (Story) => (
      <div className="relative min-h-screen bg-gray-900 p-8">
        {/* Simulated page structure with elements that match targetSelectors */}
        <nav className="mb-8 flex gap-4">
          <a href="/garage" className="bg-green-600 text-white px-4 py-2 rounded">
            Hangar
          </a>
          <a href="/garage/engineering" className="bg-blue-600 text-white px-4 py-2 rounded">
            Engineering
          </a>
        </nav>
        <div className="mission-selection-panel bg-gray-800 p-6 rounded">
          <h2 className="text-white mb-4">Mission Selection Panel</h2>
          <button className="bg-red-600 text-white px-6 py-3 rounded">
            Enter Battle
          </button>
        </div>
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
    onComplete: () => console.log('Onboarding completed'),
  },
};

export const StartFromStep2: Story = {
  args: {
    show: true,
    startStep: 1,
    onComplete: () => console.log('Onboarding completed'),
  },
};
