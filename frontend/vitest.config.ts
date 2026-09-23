import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';

import { playwright } from '@vitest/browser-playwright';

const dirname =
  typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));

// More info at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon
export default defineConfig({
  test: {
    projects: [
      {
        extends: true,
        plugins: [
          // The plugin will run tests for the stories defined in your Storybook config
          // See options at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon#storybooktest
          storybookTest({ configDir: path.join(dirname, '.storybook') }),
        ],
        test: {
          name: 'storybook',
          // BattleViewer の初回描画（WebGL 初期化 + three.js 読み込み）は並列実行時に 15 秒を超えることがある
          testTimeout: 30000,
          browser: {
            enabled: true,
            headless: true,
            // BattleViewer の Canvas がヘッドレス環境でも WebGL コンテキストを作れるよう、ソフトウェアレンダラを使う
            provider: playwright({
              launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
            }),
            instances: [{ browser: 'chromium' }],
          },
          setupFiles: ['.storybook/vitest.setup.ts'],
        },
      },
      {
        resolve: {
          alias: {
            '@': path.join(dirname, 'src'),
          },
        },
        test: {
          name: 'unit',
          environment: 'node',
          include: ['tests/unit/**/*.test.ts'],
        },
      },
    ],
  },
});
