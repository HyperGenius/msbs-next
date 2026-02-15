import type { Preview } from "@storybook/react";
import React from "react";
import { ClerkProvider } from "./mocks/clerk"; // モックを直接インポート
import "../src/app/globals.css"; // Tailwind CSS
import { Geist_Mono } from 'next/font/google';

// Next.js Fontのモック
const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
});

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    nextjs: {
      appDirectory: true,
    },
    // 背景色をアプリに合わせて暗く設定
    backgrounds: {
      default: 'dark',
      values: [
        { name: 'dark', value: '#050505' },
        { name: 'light', value: '#ffffff' },
      ],
    },
  },
  decorators: [
    (Story: any, context: any) => {
      // Storyごとのパラメータからユーザー情報を取得
      const { clerk } = context.parameters;
      
      return (
        <ClerkProvider user={clerk?.user}>
          <div className={`${geistMono.variable} font-mono antialiased`}>
            <Story />
          </div>
        </ClerkProvider>
      );
    },
  ],
};

export default preview;
