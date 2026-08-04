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
# npm run test は存在しない。必ず vitest を直接実行する
cd frontend && npx vitest run tests/unit/
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

## パイロットステータス体系

### StatKey と BonusAllocation（Phase E-1 以降）

```typescript
// frontend/src/app/onboarding/_types.ts
export type StatKey = "SHT" | "MEL" | "INT" | "REF" | "TOU" | "LUK";

// BonusAllocation = Record<StatKey, number>
// BONUS_POINTS_TOTAL = 5（サインアップウィザードのボーナス総量）
```

**`DEX` は廃止済み**。`StatKey` に `"DEX"` を追加してはいけない。

### Pilot 型のステータスフィールド（`frontend/src/types/pilot.ts`）

```typescript
sht: number;   // 射撃精度
mel: number;   // 格闘技巧
intel: number;
ref: number;
tou: number;
luk: number;
```

---

## backgrounds.json の二重管理

**同名ファイルが2箇所に存在する。両方を必ず同期して更新すること。**

| パス | 用途 |
|---|---|
| `frontend/src/data/backgrounds.json` | Next.js オンボーディングページ（`onboarding/page.tsx`）が読み込む |
| `backend/data/master/backgrounds.json` | FastAPI ルーターが読み込む |

現在のベースステータスキー: `SHT`, `MEL`, `INT`, `REF`, `TOU`, `LUK`（`DEX` は存在しない）

---

## SciFi UIコンポーネント（`src/components/ui/`）の注意点

- `SciFiSelect` は `<option>` を子要素に渡す方式ではなく、**`options: { value, label }[]` prop必須**（`SciFiSelect.tsx`）。`<SciFiSelect><option>...</option></SciFiSelect>` のような書き方はできない
- `SciFiSelect` は既定で `w-full`（幅いっぱい）。フィルタバーなどで幅を詰めたい場合、`className` に通常の `w-auto` を渡しても効かないことがある（`w-full` が base クラス文字列に先に埋め込まれており、Tailwindの生成順序次第でどちらが勝つか不定なため）。確実に上書きするには `!w-auto`（important修飾子）を使う。同様に `!px-2 !py-2 !text-xs` のようにpadding/font-sizeも上書き可能
- `SciFiButton` は `primary`/`secondary`/`accent`/`danger` の**塗りつぶしvariantのみ**で、アウトライン（枠線のみ）variantは存在しない。ボーダーのみ→hover/active時に反転する強調ボタンが欲しい場合は `SciFiButton` を使わず素の `<button>` に自前でクラスを書く（例: `border border-[#00ff41] text-[#00ff41] bg-transparent hover:bg-[#00ff41] hover:text-black`）
- `SciFiCard` の `onClick` は `() => void`（イベント引数を受け取らない）。`(e) => e.stopPropagation()` のような使い方はできない

## 強化・改造系モーダルのUI規約（Issue #413）

機体強化（`StatusTab.tsx`、`CustomizationModal` の STATUS タブ）と武器改造（`WeaponUpgradeModal.tsx`）は、レイアウト・操作感を統一している。新しく強化・改造系のUI（ステータスを段階的に上げる操作）を追加する場合は、この2つを参考に同じパターンに揃えること。

### 共通レイアウト（`StatusTab.tsx` が原型）

1ステータスにつき1行、以下の要素をこの順で並べる:

```
[ラベル]                                    [ペンディング分のコスト]
[ランクバッジ + ✨RANK UP!] [SciFiBlockIndicator] [[-] [ステップ数] [+] [1ステップ分のコスト]]
```

- **ランクバッジ + `SciFiBlockIndicator`（`components/ui/SciFiBlockIndicator.tsx`）+ `[-]`/`[+]` ステッパー** の3点セットを1行に横並びする。ステップ数はコンポーネント内 state（`pendingSteps: Record<string, number>`）で保持し、実際のAPI呼び出しは行わずクライアント側でシミュレーションしてプレビューする
- 複数ステータスがある場合も、末尾に置いた **1つの `HoldSciFiButton`（長押し確定）でまとめて一括確定**する（`StatusTab.tsx` の `handleApplyAll` / `WeaponUpgradeModal.tsx` の `handleApplyAll` を参照）。ステータスごとに個別の確定ボタンを設けない
- 先頭に所持クレジットの「現在 ➔ 変更後」表示（ペンディングがある時だけ矢印以降を表示、支払い可能なら `text-[#00f0ff]`、不可なら `text-red-400`）を置く

### 生の数値（raw value）を表示しない

**ステータスの実数値（例: 威力「200」「→ 205」、命中率「85.0%」など）はUIに出力しない。** ランクバッジ（S〜E）と `SciFiBlockIndicator` の埋まり具合のみで、現在の強さ・改造後の変化を表現する。理由: 武器改造UIで一度、実数値を表示する行を追加したが、バックエンドAPIの `current_value`/`new_value` の意味（実効値かボーナス値か）を取り違えて誤表示するバグを生んだ経緯があり、そもそも生数値を出さない方針に倒すことで作り込みとバグの両方を避けている（`WeaponUpgradeModal.tsx` 参照。武器改造プレビューAPI自体は実効値を返すよう既に修正済みだが、UIでは使っていない）。

### コスト計算式はクライアント側にバックエンドと同じ式を複製する

`StatusTab.tsx`（`EngineeringService` の式）・`WeaponUpgradeModal.tsx`（`WeaponEngineeringService` の式）はいずれも、コスト計算・上限キャップの式をクライアント側に複製し、プレビュー用APIを都度呼ばずに `+`/`-` ボタン操作を即座に反映させている。**バックエンド側の定数（`BASE_*_COST`、除数、増分、上限）を変更した場合は、対応するフロントエンドの定数も必ず同期して更新すること。** 式がずれると、クライアント側の見積もりと実際にAPIで確定した結果が食い違う（コストや上限判定がずれる）。

### タブ切り替えのあるモーダルは固定高さにする（`max-h` にしない）

`CustomizationModal.tsx`（STATUS/TERRAIN/LOADOUT/TACTICS のタブ切り替え）のように**タブでコンテンツが差し替わるモーダル**は、外側コンテナに `h-[85dvh]` のような**固定高さ**を指定し、タブ内コンテンツ側を `overflow-y-auto flex-1` でスクロールさせること。`max-h-[85dvh]`（上限のみ）にすると、タブごとにコンテンツの実高さが異なるためモーダル自体の高さが伸縮し、ヘッダー・タブバーの表示位置がタブ切り替えのたびにずれてユーザーが混乱する（一度この実装で回帰させた経緯があるため要注意。Issue #413）。一方、タブが無く単一ビューのモーダル（`WeaponChangeModal.tsx`、`SciFiModal` ベースのモーダル全般）はコンテンツ量に応じて高さが変わって構わないため `max-h-[85dvh]` のままでよい。

## アイコンの扱い

プロジェクトにアイコンライブラリ（lucide-react, react-icons, heroicons等）は**導入されていない**。UIにアイコンが必要な場合は依存追加を避け、`stroke="currentColor"` ベースの最小限のインラインSVGをコンポーネント内にローカル関数として定義する。テキスト絵文字（`✕`など）で足りる場合はそちらでも可。

- 単一コンポーネント内でしか使わない一時的なアイコン: そのファイル内にローカル関数として定義する（例: `WeaponInventoryList.tsx` の `FilterIcon` / `TypeIcon` / `SortIcon` / `EmptyBoxIcon`）
- 複数コンポーネントで共有するアイコン: `frontend/src/components/icons/TablerIcons.tsx` に集約する。Header/BottomNav等のグローバルUIは[Tabler Icons](https://tabler.io/icons)（outline, MIT License）のSVGパスをここに複製して使う。**新しいグローバルアイコンが必要になった場合も、このファイルに追記し、他のアイコンセットと混在させないこと**（`BottomNav.tsx`, `Avatar.tsx` が利用例）

## SWRフックはコンポーネント側で直接呼んでよい（プロップドリリング不要）

親コンポーネントが既に同じデータソースを別条件で fetch している場合でも、子コンポーネントが異なるクエリパラメータで取得したい時は、子側で直接 SWR フック（`usePlayerWeapons(unequippedOnly)` など）を呼び出してよい。SWR は同一URLをグローバルキャッシュキーとして重複排除するため、条件が親と同じ（例: フィルタOFF時）であれば追加のネットワークリクエストは発生せず、条件が異なる（例: `?unequipped=true` を付けたい時）場合だけ新しいキーとして取得される。`playerWeapons` を毎回 prop で渡す設計より、こちらの方が「必要な時だけ絞り込みクエリを叩く」実装をシンプルに保てる（`WeaponInventoryList.tsx` 参照）。

## 武器の装備状態の正（Garage関連UI）

`MobileSuit.weapons`（JSON列、バトルエンジン用スナップショット）と `PlayerWeapon.equipped_ms_id`/`equipped_slot`（正規化された装備状態）の**2つの情報源が並存**している。Garage画面などで「どの武器がどのMSに装備されているか」を表示する場合は、必ず `PlayerWeapon` 側のフィールドを正として使うこと。`MobileSuit.weapons` は装備操作のたびに追随更新されるが、あくまでバトルエンジンが直接参照するためのスナップショットであり、UI表示のソースにしない。

## ルートレイアウトとページルート要素の規約（Issue #409）

`frontend/src/app/layout.tsx` の `RootLayout` は次の構造になっている。

```tsx
<body className="... flex flex-col h-[100dvh] overflow-hidden md:h-auto md:min-h-screen md:overflow-visible">
  <Header />
  <main className="flex-1 overflow-y-auto md:overflow-visible">
    {children}
  </main>
  {/* BottomNavはfixed配置のためflowから外れる。mainの高さをその分だけ事前に縮めておくためのスペーサー */}
  <div className="h-16 shrink-0 md:hidden" aria-hidden="true" />
  <BottomNav />
</body>
```

- モバイル幅では `body` が `h-[100dvh] overflow-hidden` で画面高さに固定され、`main` が `flex-1 overflow-y-auto` でスクロール領域になる。`BottomNav`（`fixed bottom-0 h-16 md:hidden`）はflowから外れるため、`main` と `BottomNav` の間に高さ `h-16` のスペーサーを兄弟として置くことで `main` の実高さ（`flex-1` の配分結果）をあらかじめBottomNav分だけ縮めてある。
- **`main` 自体（`overflow-y-auto` が設定されたスクロールコンテナ）に `padding-bottom` を足してBottomNav分の余白を作ってはいけない。** `overflow-y-auto` 要素の `padding-bottom` は `box-sizing` に関わらず常に `scrollHeight` に加算されるため、`children` の実コンテンツが短くてもスクロールが発生してしまう回帰を招く（一度この実装で規約違反をやってしまった経緯があるため要注意）。BottomNav分のスペース確保は必ず上記のflexスペーサー方式で行う。
- 各ページ（`src/app/**/page.tsx`）のルート要素は、この `<main>` に**ネストされる**ことを前提に書くこと。
  - `min-h-screen`（`min-height: 100vh`）を指定しない。親の `<main>` の実高さ（＝ビューポート − Header − BottomNavスペーサー）を最小値にしたい場合は `min-h-full` を使う。`min-h-screen` を使うと、コンテンツが無い/短いページでも常にビューポート全体以上の高さが強制され、外側 `main` の `scrollHeight` が `clientHeight` を上回って不要な縦スクロールが発生する。
  - ルート要素に `<main>` タグを使わない。`layout.tsx` 側で既に `<main>` があるため、ページ側でも使うと `<main>` が二重にネストされる（landmarkの重複）。`<div>` を使う。

詳細な経緯は `docs/features/layout-bottomnav-spacing.md` を参照。

## よくあるハマりポイント

| 状況 | 対処 |
|---|---|
| `npx tsc` が失敗する | `cd frontend && ./node_modules/.bin/tsc --noEmit` を使う |
| Vitest で `vi is not defined` | `import { vi } from "vitest"` を明示的に書く（globals 無効） |
| `vi.mock` が hoisting されない | `vi.mock(...)` はファイル先頭の `import` より前に動作する（Vitest が自動 hoist） |
| SSR で `getAuthToken` が null を返す | 正常動作。`window.Clerk` はクライアントサイドのみ存在する |
| `types/battle.ts` の名前衝突 | バトル実装型は `battleCore.ts` に置く。`battle.ts` はバレル専用 |
| モーダルが BottomNav の裏に隠れる | `BottomNav` は `z-50 h-16 fixed bottom-0 md:hidden`。モーダルは `z-[60]` 以上にすること。また `items-center p-4` で上下均等マージンを確保すること。可能なら独自に `fixed inset-0` を書かず共通コンポーネント `components/ui/SciFiModal.tsx`（`z-[60]` 固定、`max-h-[85dvh]` + `overflow-y-auto`、Esc/オーバーレイクリックで閉じる実装済み）を使う。過去に `CustomizationModal.tsx`（`z-40`）と、その上に重ねて開く `WeaponChangeModal.tsx`（`z-50`）が `SciFiModal` 導入前の実装のまま取り残され、この規約を満たしておらずBottomNavの裏に隠れる不具合になったことがある（Issue #413で `z-[60]`/`z-[70]` に修正）。モーダルの上にさらにモーダルを重ねる場合は、外側より高い `z-index`（例: `z-[70]`）にすること |
| モバイルでコンテンツ末尾が BottomNav の裏に隠れる／逆にコンテンツが無いのに縦スクロールできる | `frontend/CLAUDE.md`「ルートレイアウトとページルート要素の規約」参照。`main`（`overflow-y-auto`）自体に `padding-bottom` を足すと `scrollHeight` が常に加算されズレる。BottomNav分のスペースは `layout.tsx` 側のflexスペーサーで確保済みなので、ページ側は `min-h-screen` を使わない |
| `SciFiSelect` の幅・paddingが `className` で変わらない | base クラスに `w-full`/`px-4 py-2` が先に入っているため、`!w-auto` のように important修飾子を付けて上書きする |
| `getRankColor`（`utils/rankUtils.ts`）でランクEが灰色になる | 元々 `S`〜`D` のみ定義され `E` は `default` にフォールバックしていた。`E` 用のケースを追加済みだが、ランク関連の新規UIを書く際は S〜E 全ケースが期待通り色分けされるか確認する |
| 未ログイン状態で `/garage` 等の保護ルートにアクセスすると 404 になる | Clerkのルート保護（`protect-rewrite`）による意図した挙動。プレビュー確認時はログインが必要で、このリポジトリにはClerkテストトークンを使ったE2E（Playwright等）の仕組みが無いため、認証必須ページのUI動作は `tsc`/`vitest`/`next build` のみで確認し、実ログインでの見た目確認は別途手動で行う旨を明記する |
