import type { Meta, StoryObj } from '@storybook/react';
import Header from './Header';

const meta: Meta<typeof Header> = {
  title: 'Components/Header',
  component: Header,
};

export default meta;
type Story = StoryObj<typeof Header>;

// 未ログイン
export const SignedOut: Story = {
  parameters: {
    clerk: { user: null },
  },
};

// ログイン済み
export const SignedIn: Story = {
  parameters: {
    clerk: {
      user: {
        id: 'user_123',
        fullName: 'Amuro Ray',
        imageUrl: '[https://i.pravatar.cc/300](https://i.pravatar.cc/300)',
      },
    },
  },
};
