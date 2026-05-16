# CLAUDE.md 

このファイルは、Claude Code がこのリポジトリの`frontend`ディレクトリで作業する際の規約・構造・判断基準を記述します。

## サービス層の構造

`frontend/src/services/` は **ドメインごとに分割されたファイル群** と、後方互換バレルファイルで構成されます。

```
services/
├── api.ts          ← バレル（全ドメインを re-export）後方互換のため維持
├── auth.ts         ← 認証ユーティリティ（全サービスが import）
├── battle.ts       ← バトル結果の取得・既読マーク
├── entry.ts        ← バトルエントリー
├── friends.ts      ← フレンド申請・承認・拒否・解除
├── leaderboard.ts  ← リーダーボード・プレイヤー検索
├── mobileSuit.ts   ← 機体の取得・更新
├── pilot.ts        ← パイロット CRUD・ステータス配分
├── shop.ts         ← ショップ商品一覧・購入
├── skills.ts       ← スキル習得・レベルアップ
├── teams.ts        ← チーム作成・招待・Ready・離脱・エントリー
└── upgrades.ts     ← 機体強化プレビュー・実行
```

### auth.ts が提供するもの

| エクスポート | 説明 |
|---|---|
| `API_BASE_URL` | バックエンド URL（環境変数 or `http://127.0.0.1:8000`） |
| `getAuthToken()` | Clerk セッショントークンを取得（SSR では null） |
| `fetcher` | SWR 用の認証付き fetch 関数 |
| `useAuthFetcher()` | React Hook（Clerk の `useAuth` を使用） |
| `authKey(url, isLoaded, isSignedIn)` | SWR キーを認証状態に応じて返す |

### 新しいドメインサービスを追加するとき

1. `services/<domain>.ts` を作成してロジックを記述
2. `services/api.ts` に `export * from "./<domain>"` を追加
3. 既存の `@/services/api` インポートは引き続き動作する（バレル経由）

---

## 型定義層の構造

`frontend/src/types/` も同様にドメイン分割＋バレルパターンです。

```
types/
├── battle.ts       ← バレル（全型を re-export）後方互換のため維持
├── admin.ts        ← 管理者用型
├── battleCore.ts   ← バトルログ・バトル結果・BattleRoom・BattleEntry など
├── geometry.ts     ← Position 型など空間座標
├── leaderboard.ts  ← ランキング・EnrichedPlayerProfile
├── mobileSuit.ts   ← MobileSuit・戦術設定など
├── pilot.ts        ← Pilot・Faction・ステータス
├── shop.ts         ← ショップ商品・強化プレビュー・武器管理
├── skill.ts        ← スキル定義・SkillId
├── social.ts       ← Friend・Team・チームメンバー
└── weapon.ts       ← Weapon・WeaponType
```

> **注意**: `battle.ts` はバレルとして残す。実装ファイルは `battleCore.ts` と命名する（名前衝突回避）。

### 型ファイルの依存関係（循環参照なし）

```
geometry → (なし)
weapon   → (なし)
mobileSuit → geometry, weapon
battleCore → geometry, mobileSuit
pilot      → (なし)
skill      → pilot
shop       → weapon, mobileSuit
leaderboard → mobileSuit
social     → (なし)
admin      → weapon
```

---

## サインアップウィザードの構造

`frontend/src/app/sign-up/[[...sign-up]]/` は **5フェーズのウィザード**です。

```
sign-up/[[...sign-up]]/
├── page.tsx              ← JSX オーケストレーター（ロジックなし）
├── _constants.ts         ← 定数・ユーティリティ関数（WizardPhase, BONUS_POINTS_TOTAL など）
├── _hooks/
│   └── useSignUpFlow.ts  ← ウィザード全ステート＆ハンドラー
└── _components/
    ├── PhaseIndicator.tsx ← フェーズ進捗バー
    └── （各フェーズコンポーネント）
```

### useSignUpFlow の重要な設計判断

- `completedAuthRef`: Phase 3 完了後のリダイレクトを防ぐフラグ
- `resumedAtPhase3`: セッション再開時に「戻る」ボタンを無効にする
- `handlePhase4Submit`: `useCallback` でラップ（Phase 5 のリトライボタンが参照するため）

---

## コーディング規約

### 日本語コメント

**すべての新規ファイルと関数には日本語でコメントを書く。**

```typescript
/** パイロット情報を取得する（404 は isNotFound フラグとして扱い、エラーにしない） */
export function usePilot() { ... }

// スキルポイントが不足している場合はここで例外を投げる
if (!response.ok) { ... }
```

- 関数レベル: `/** ... */` JSDoc スタイル
- インライン: `// ...` 一行コメント
- 非自明な理由がある箇所のみ書く（自明な処理には不要）

### ファクション別テーマカラー

| ファクション | テーマ | カラー |
|---|---|---|
| FEDERATION | `accent` | `#00f0ff`（シアン） |
| ZEON | `secondary` | `#ffb000`（オレンジ） |

ユーティリティ関数は `_constants.ts` の `themeTextClass(v)` 等を使用する。

---

## テスト規約

### テストファイルの配置

```
frontend/tests/unit/
├── authUtils.test.ts             ← auth.ts の純粋関数
├── signUpConstants.test.ts       ← _constants.ts の関数・定数
├── pilotService.test.ts          ← pilot.ts の async 関数
├── mobileSuitService.test.ts     ← mobileSuit.ts の async 関数
├── battleService.test.ts         ← battle.ts の async 関数
├── entryService.test.ts          ← entry.ts の async 関数
├── shopService.test.ts           ← shop.ts の async 関数
├── skillsService.test.ts         ← skills.ts の async 関数
├── upgradeService.test.ts        ← upgrades.ts の async 関数
├── teamsService.test.ts          ← teams.ts の async 関数
└── friendsService.test.ts        ← friends.ts の async 関数
```

### テストに含めない対象

- **SWR フック**（`usePilot`, `useCurrentTeam` など）: `environment: 'node'` のため jsdom が使えず React レンダリング不可
- React コンポーネント: React Testing Library が未設定

### 標準的なサービステストのパターン

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { someFn } from "@/services/domain";

// getAuthToken だけモック、他は実装をそのまま使う
vi.mock("@/services/auth", async () => {
  const actual = await vi.importActual<typeof import("@/services/auth")>("@/services/auth");
  return { ...actual, getAuthToken: vi.fn().mockResolvedValue("test-token") };
});

/** 成功レスポンスを生成するヘルパー */
const mockOk = (data: unknown = {}) =>
  ({ ok: true, json: () => Promise.resolve(data) } as unknown as Response);

/** APIエラーレスポンスを生成するヘルパー */
const mockErr = (detail: string, status = 400) =>
  ({
    ok: false,
    status,
    statusText: "Bad Request",
    json: () => Promise.resolve({ detail }),
  } as unknown as Response);

beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
afterEach(() => { vi.unstubAllGlobals(); });
```

### 各サービス関数でカバーすべきテストケース

1. 成功時に期待する値を返す
2. 正しい HTTP メソッドとエンドポイント URL で fetch を呼ぶ
3. 正しい JSON ボディを送信する
4. `Authorization: Bearer <token>` ヘッダーを付与する
5. エラーレスポンスの `detail` フィールドでエラーを投げる
6. `detail` がない場合はステータスコードを含むフォールバックメッセージを投げる

### テストの実行

```bash
cd frontend && npm run test
```

---

## バレルファイルパターン（後方互換性の維持）

既存の import パスを壊さずにファイルを分割するには、元のファイルをバレルに書き換える。

```typescript
// services/api.ts（バレル化後）
export * from "./pilot";
export * from "./mobileSuit";
// ... 他のドメイン
```

これにより `import { usePilot } from "@/services/api"` は引き続き動作する。

---

## よくあるハマりポイント

| 状況 | 対処 |
|---|---|
| `npx tsc` が失敗する | `cd frontend && ./node_modules/.bin/tsc --noEmit` を使う |
| Vitest で `vi is not defined` | `import { vi } from "vitest"` を明示的に書く（globals 無効） |
| `vi.mock` が hoisting されない | `vi.mock(...)` はファイル先頭の `import` より前に動作する（Vitest が自動 hoist） |
| SSR で `getAuthToken` が null を返す | 正常動作。`window.Clerk` はクライアントサイドのみ存在する |
| `types/battle.ts` の名前衝突 | バトル実装型は `battleCore.ts` に置く。`battle.ts` はバレル専用 |
