# 📘 MSBS-Next: Storybook 導入・設定ガイド

このドキュメントでは、Next.js + Tailwind CSS + Clerk (Auth) 環境における Storybook の導入と設定手順について記述します。
特に、認証機能（Clerk）をアドオンを使わずに手動でモック化し、安定して動作させる方法を採用しています。

## 1. インストールと初期化

`frontend` ディレクトリで以下のコマンドを実行し、Storybook を初期化します。

```bash
cd frontend
npx storybook@latest init
```

* プロジェクトタイプを聞かれた場合は `Next.js` を選択してください。
* Storybook 10.x 系では Vite ベースの構成（`@storybook/nextjs-vite`）がインストールされます。
* 初期化時に生成されるサンプル Story は、必要に応じて削除できます（`src/stories` ディレクトリ）。

---

## 2. Clerk (認証) のモック化

Clerk のフック（`useUser`, `useAuth`）やコンポーネント（`SignedIn`, `UserButton`）を Storybook 上で再現するためのモックファイルを作成します。

**ファイル:** `frontend/.storybook/mocks/clerk.tsx` (新規作成)

```tsx
import React, { createContext, useContext } from 'react';

// 認証状態を保持するコンテキスト
const ClerkMockContext = createContext<{ user: any } | null>(null);

// モック用の Provider
// StorybookのDecoratorからユーザー情報を受け取ります
export const ClerkProvider = ({ children, user }: { children: React.ReactNode; user?: any }) => {
  return (
    <ClerkMockContext.Provider value={user ? { user } : null}>
      {children}
    </ClerkMockContext.Provider>
  );
};

// --- 以下、Clerkコンポーネント/フックのモック ---

export const SignedIn = ({ children }: { children: React.ReactNode }) => {
  const context = useContext(ClerkMockContext);
  return context?.user ? <>{children}</> : null;
};

export const SignedOut = ({ children }: { children: React.ReactNode }) => {
  const context = useContext(ClerkMockContext);
  return !context?.user ? <>{children}</> : null;
};

export const UserButton = () => {
  const context = useContext(ClerkMockContext);
  const imageUrl = context?.user?.imageUrl;
  
  return (
    <div className="w-8 h-8 rounded-full overflow-hidden border-2 border-white bg-gray-700">
      {imageUrl ? (
        <img src={imageUrl} alt="User" className="w-full h-full object-cover" />
      ) : (
        <div className="flex items-center justify-center w-full h-full text-xs font-bold text-white">
          U
        </div>
      )}
    </div>
  );
};

export const SignInButton = ({ children }: { children: React.ReactNode }) => {
  return <button onClick={() => alert("Sign In Clicked (Storybook Mock)")}>{children}</button>;
};

export const useUser = () => {
  const context = useContext(ClerkMockContext);
  return {
    user: context?.user || null,
    isLoaded: true,
    isSignedIn: !!context?.user,
  };
};

export const useAuth = () => {
  const context = useContext(ClerkMockContext);
  return {
    isLoaded: true,
    isSignedIn: !!context?.user,
    userId: context?.user?.id,
    getToken: () => Promise.resolve('mock-token'),
    signOut: () => Promise.resolve(),
  };
};

```

---

## 3. Vite Alias の設定 (`main.ts`)

アプリケーションコードが `@clerk/nextjs` をインポートした際、自動的に上記のモックファイルを読み込むように Vite のエイリアスを設定します。

**ファイル:** `frontend/.storybook/main.ts`

```ts
import type { StorybookConfig } from "@storybook/nextjs-vite";
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

// ESM環境での __dirname の代替
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const config: StorybookConfig = {
  stories: ["../src/**/*.mdx", "../src/**/*.stories.@(js|jsx|mjs|ts|tsx)"],
  addons: [
    "@chromatic-com/storybook",
  ],
  framework: {
    name: "@storybook/nextjs-vite",
    options: {},
  },
  staticDirs: ["../public"],
  // Clerkのインポートをモックファイルに差し替える設定
  viteFinal: async (config) => {
    if (config.resolve) {
      config.resolve.alias = {
        ...config.resolve.alias,
        '@clerk/nextjs': resolve(__dirname, './mocks/clerk.tsx'),
      };
    }
    return config;
  },
};
export default config;
```

### 重要な変更点

- **Vite ベース**: Storybook 10.x では `@storybook/nextjs-vite` を使用
- **`viteFinal`**: Webpack の代わりに Vite の設定をカスタマイズ
- **ESM 対応**: `__dirname` を ESM 環境で使用するため、`fileURLToPath` と `dirname` を使用
- **addon の最小化**: Storybook 10.x では多くの機能が組み込まれているため、必要最小限の addon のみを指定

---

## 4. プレビュー設定 (`preview.tsx`)

Tailwind CSS の読み込みと、認証状態を注入するための Decorator を設定します。

**ファイル:** `frontend/.storybook/preview.tsx`

> **注意**: JSX を含むため、ファイル拡張子は `.tsx` にしてください（`.ts` ではエラーになります）。

```tsx
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
```

### 重要な変更点

- **React を明示的にインポート**: JSX を使用するため、`React` をインポートする必要があります
- **モックを直接インポート**: `./mocks/clerk` から直接インポートすることで、型エラーを回避します
- **ファイル拡張子**: `.tsx` を使用（JSX を含むため）

---

## 5. Story の作成例

### 例1: 認証が必要なコンポーネント (Header)

`parameters.clerk.user` にオブジェクトを渡すことでログイン状態、`null` を渡すことでログアウト状態を再現できます。

```tsx
// frontend/src/components/Header.stories.tsx
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

```

### 例2: チュートリアルなど、特定の背景が必要なコンポーネント

`decorators` を使って、コンポーネントが表示されるための「ダミーの親要素」を作ることができます。

```tsx
// frontend/src/components/Tutorial/OnboardingOverlay.stories.tsx
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

```

## 6. 実行

```bash
npm run storybook
```

ブラウザで `http://localhost:6006` が開き、作成した UI コンポーネントを確認できます。

---

## 7. トラブルシューティング

### デフォルトの Story ファイルでエラーが発生する場合

初期化時に生成されるサンプル Story（`src/stories` ディレクトリ）が依存関係のエラーを引き起こすことがあります。その場合は、以下のコマンドで削除してください：

```bash
rm -rf frontend/src/stories
```

### ポートが使用中の場合

デフォルトのポート 6006 が使用中の場合、Storybook は自動的に別のポート（6007 など）を提案します。または、以下のように明示的にポートを指定できます：

```bash
npm run storybook -- -p 6007
```

### TypeScript エラーが発生する場合

- `preview.tsx` のファイル拡張子が `.tsx` であることを確認してください（`.ts` ではエラーになります）
- `main.ts` で ESM 環境対応の `__dirname` 定義があることを確認してください

---

## 8. まとめ

この設定により、以下が可能になります：

- ✅ Clerk 認証を使用するコンポーネントを Storybook で動作させる
- ✅ ログイン状態とログアウト状態を Story ごとに切り替える
- ✅ Next.js アプリと同じ Tailwind CSS スタイルを使用
- ✅ Vite ベースの高速な開発環境
