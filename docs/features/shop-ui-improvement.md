# ショップ UI 抜本改善提案

**バージョン**: 1.1.0  
**作成日**: 2026-06-01  
**最終更新**: 2026-06-01  
**ステータス**: Phase 1 + Phase 2 + Phase 3 実装済み（Issue #377）  
**対象ファイル**: `frontend/src/app/shop/page.tsx`

---

## 1. 概要と目的

ショップ画面（MOBILE SUIT SHOP / WEAPON SHOP）は現状、Mobile Suits と Weapons のアイテムをグリッドで縦積み表示するだけの構成になっている。この構成では「今の所持金で何が買えるのか」が一目でわからず、購入判断のたびにスクロールしてクレジット残高を確認し直す必要がある。また、カード1枚が縦に長いため1画面に表示できるアイテム数が少なく、比較・選択の体験が著しく損なわれている。

本ドキュメントは現状の問題点を整理し、「縦にだらだら並ぶアイテムリスト」から**「今の所持金で何を買うかが一目でわかる選択画面」**への抜本的なリデザインの方向性と具体的な仕様を示す。

---

## 2. 現状の課題

### 2.1 問題点一覧

| # | カテゴリ | 問題の説明 | 影響度 |
|---|----------|-----------|--------|
| 1 | 情報設計 | 所持クレジットがページ上部に1回のみ表示され、スクロール中は消えて購入判断に使えない | 高 |
| 2 | 一覧性 | 購入可能/不可の区別が `opacity-60` のみで、視覚的なメリハリがない | 高 |
| 3 | 比較性 | カード1枚が縦に長く、モバイルでは1画面に1〜2件しか表示できない | 高 |
| 4 | 可視化 | スペックが数値とテキストの羅列のみ。ランクの視覚的表現がなく強弱が把握しにくい | 高 |
| 5 | モバイルUX | 購入ボタン（HoldSciFiButton）がカード内に埋まり、スクロールしないと到達できない | 中 |
| 6 | フィルタ | 購入可能なアイテムだけに絞り込む手段がなく、買えないアイテムがノイズになる | 中 |

### 2.2 現状のコンポーネント構造

```
shop/page.tsx（402行）
├── パイロット情報ヘッダー（credits 表示）
├── タブ: [Mobile Suits] [Weapons]
├── Mobile Suits タブ
│   └── grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
│       └── SciFiCard × N（縦長カード）
│           ├── アイテム名・価格・説明文
│           ├── スペック（HP / 装甲 / 機動性）数値表示
│           ├── 搭載武器情報
│           └── HoldSciFiButton または 購入不可ボタン
└── Weapons タブ
    └── grid-cols-1 md:grid-cols-2 lg:grid-cols-3
        └── SciFiCard × N（縦長カード）
            ├── 武器名・価格・説明文
            ├── スペック（6属性）数値表示
            └── HoldSciFiButton または 購入不可ボタン
```

---

## 3. 改善方針

### 3.1 設計思想

> **「数字を確認する画面」から「ビルドを選ぶ画面」へ**

- プレイヤーが所持金の範囲内で「どれを買うか」の判断を即座に下せること
- アイテムの強弱をランクで視覚的に把握できること
- モバイルでも快適に操作できること（親指ゾームの活用、Progressive Disclosure）

### 3.2 優先度分類

| 優先度 | 内容 |
|--------|------|
| **P0 必須** | Sticky クレジットヘッダー、アフォーダビリティフィルター、不足額表示 |
| **P1 重要** | コンパクトカード + 詳細モーダル（Progressive Disclosure） |
| **P2 改善** | スペックバー（ランク色連動）、PC向け2カラムレイアウト |
| **P3 細部** | 購入後クレジット残高アニメーション、ソート機能 |

---

## 4. 各改善案の詳細仕様

### 4.1 Sticky クレジットヘッダー

スクロールしても常に画面上部に表示される、クレジット残高・タブ・フィルターの統合ヘッダー。

#### モックアップ（モバイル）

```
┌────────────────────────────────────┐
│  CREDITS  12,500 C                 │  ← 常に固定表示
│  [Mobile Suits]  [Weapons]         │  ← タブ切り替え
│  [全て]  [購入可能のみ]             │  ← フィルターチップ
└────────────────────────────────────┘
```

#### 仕様

| 項目 | 内容 |
|------|------|
| 配置 | `position: sticky; top: 0` でスクロール追従 |
| 背景 | `#0a0a0a` + `border-b border-[#00ff41]/30`（アイテムリストとの境界） |
| クレジット表示 | `usePilot()` から取得。購入後は SWR revalidate でリアルタイム更新 |
| フィルター | 「全て」「購入可能のみ」の2択チップ。状態は `filter` ステートで管理 |

---

### 4.2 コンパクトカード設計（一覧ビュー）

縦長カードを廃止し、カード高さ約80pxのコンパクトな横長カードに刷新。1画面に4〜5件表示できるようにする。

#### Mobile Suits カードモックアップ

```
┌────────────────────────────────────────────┐
│ RX-78-2 ガンダム              [購入可]      │
│ HP[A]  装甲[A]  機動[S]                    │
│ 搭載: ビームライフル（BEAM）   3,200 C  →  │
└────────────────────────────────────────────┘
```

#### Weapons カードモックアップ

```
┌────────────────────────────────────────────┐
│ ビームライフル                [購入可]      │
│ 攻撃[A]  射程[S]  命中[B]                  │
│ 遠距離 / EN消費あり           1,800 C  →  │
└────────────────────────────────────────────┘
```

#### カード仕様

| 要素 | 仕様 |
|------|------|
| 購入可能バッジ | 緑ボーダー + `購入可` ラベル（`text-[#00ff41]`） |
| 購入不可 | グレーボーダー + 不足額表示 `(-800 C)`（`text-red-400`） |
| ランクバッジ | `getRank()` / `getWeaponRank()` でランク算出、`getRankColor()` で色付け |
| タップ領域 | カード全体をクリッカブルに（詳細モーダルを開く） |
| グリッド | モバイル1列 → `md:grid-cols-2` → `lg:grid-cols-3` |

---

### 4.3 詳細モーダル（Progressive Disclosure）

カードタップで `SciFiPanel` ベースのモーダルが開き、フル仕様と購入ボタンを表示する。

#### Mobile Suits 詳細モーダルモックアップ

```
┌──────────────────────────────────────────┐
│  [×]  RX-78-2 ガンダム                   │
│  ─────────────────────────────────────  │
│  説明テキスト（description）              │
│  ─────────────────────────────────────  │
│  最大耐久  ████████░░  1800  [A]          │
│  装甲      ████████░░    85  [A]          │
│  機動性    ██████████   2.0  [S]          │
│  索敵範囲  ██████░░░░   350  [B]          │
│  ─────────────────────────────────────  │
│  搭載武器: ビームライフル                  │
│  種別: BEAM  攻撃:250[A]  射程:500[S]     │
│  命中:80%[A]  適正距離: 遠距離            │
│  ─────────────────────────────────────  │
│  所持金:  12,500 C                        │
│  価格:     3,200 C                        │
│  残高:     9,300 C  ✓                    │
│                                          │
│  [長押しで購入 (HOLD TO BUY)]            │  ← 親指ゾーン
└──────────────────────────────────────────┘
```

#### Weapons 詳細モーダルモックアップ

```
┌──────────────────────────────────────────┐
│  [×]  ビームライフル                      │
│  ─────────────────────────────────────  │
│  説明テキスト（description）              │
│  ─────────────────────────────────────  │
│  攻撃力    ████████░░   250  [A]          │
│  射程      ██████████   500  [S]          │
│  命中率    ████████░░    80  [A]          │
│  適正距離  遠距離（500m超）               │
│  減衰率    [S]  弾数: あり  EN消費: あり  │
│  ─────────────────────────────────────  │
│  所持金:   12,500 C                       │
│  価格:      1,800 C                       │
│  残高:     10,700 C  ✓                   │
│                                          │
│  [長押しで購入 (HOLD TO BUY)]            │
└──────────────────────────────────────────┘
```

#### モーダル仕様

| 項目 | 内容 |
|------|------|
| コンテナ | `SciFiPanel` + `fixed inset-0 z-50` のオーバーレイ |
| スペックバー | `SciFiProgress`（既存コンポーネント）を流用 |
| ランク表示 | `getRank()` / `getWeaponRank()` + `getRankColor()` で色付け |
| 購入ボタン | モーダル最下部（親指ゾーン）に `HoldSciFiButton` を固定配置 |
| 購入不可時 | `HoldSciFiButton` の上に「所持金不足（-800 C）」を赤表示 |
| 閉じる | 右上 `[×]` ボタン + オーバーレイ背景クリックで閉じる |

---

### 4.4 PC向け 2カラムレイアウト（lg 以上）

lg（1024px）以上では、左にカードリスト・右に詳細パネルを並べるサイドバイサイドレイアウトに切り替える。モーダルではなくインライン表示にすることで、PC のワイドスペースを有効活用する。

#### モックアップ

```
┌────────────────────────────────────────────────────────────────────┐
│  MOBILE SUIT SHOP                         CREDITS: 12,500 C        │
│  [Mobile Suits]  [Weapons]     [全て]  [購入可能のみ]              │
├──────────────────────────────┬─────────────────────────────────── │
│  ガンダム  HP[A] ARM[A] MOB[S]│  RX-78-2 ガンダム                  │
│  ザク      HP[B] ARM[A] MOB[B]│  ─────────────────────────────   │
│  ドム      HP[A] ARM[S] MOB[C]│  最大耐久  ████████░░  1800  [A]  │
│  ゲルググ  HP[S] ARM[A] MOB[B]│  装甲      ████████░░    85  [A]  │
│  ...                         │  機動性    ██████████   2.0  [S]  │
│                              │  ─────────────────────────────   │
│                              │  [長押しで購入 (HOLD TO BUY)]     │
└──────────────────────────────┴─────────────────────────────────── ┘
```

#### レイアウト仕様

| 項目 | 内容 |
|------|------|
| グリッド | `lg:grid lg:grid-cols-[5fr_7fr]` の2カラム |
| 左ペイン | コンパクトカードの縦スクロールリスト |
| 右ペイン | 選択中アイテムの詳細（`sticky top-[ヘッダー高]`で追従） |
| 初期状態 | リスト先頭のアイテムを選択済み状態で表示 |
| モバイル | `lg` 未満ではカードタップ → モーダル表示（4.3 の仕様に従う） |

---

## 5. コンポーネント設計案

### 5.1 ファイル構成（提案）

```
frontend/src/app/shop/
├── page.tsx                           ← 既存（リファクタリング対象）
└── _components/
    ├── ShopCreditHeader.tsx           ← 新規: Sticky クレジット + タブ + フィルター
    ├── MobileSuitCard.tsx             ← 新規: コンパクトカード（MS用）
    ├── WeaponCard.tsx                 ← 新規: コンパクトカード（武器用）
    ├── MobileSuitDetailPanel.tsx      ← 新規: 詳細表示（モーダル兼インラインパネル）
    └── WeaponDetailPanel.tsx          ← 新規: 詳細表示（モーダル兼インラインパネル）
```

### 5.2 主要Props設計

```typescript
// ShopCreditHeader
interface ShopCreditHeaderProps {
  credits: number;
  activeTab: "mobile_suits" | "weapons";
  onTabChange: (tab: "mobile_suits" | "weapons") => void;
  filter: "all" | "affordable";
  onFilterChange: (filter: "all" | "affordable") => void;
}

// MobileSuitCard（コンパクト）
interface MobileSuitCardProps {
  listing: ShopListing;
  credits: number;
  onSelect: (id: string) => void;
  isSelected?: boolean;  // PC 2カラム時の選択状態
}

// WeaponCard（コンパクト）
interface WeaponCardProps {
  listing: WeaponListing;
  credits: number;
  onSelect: (id: string) => void;
  isSelected?: boolean;
}

// MobileSuitDetailPanel
interface MobileSuitDetailPanelProps {
  listing: ShopListing;
  credits: number;
  isPurchasing: boolean;
  onPurchase: (id: string) => void;
  onClose?: () => void;  // モーダル時のみ使用（PC インラインでは不要）
  isModal?: boolean;     // true: モーダル表示 / false: インライン表示
}
```

### 5.3 再利用する既存リソース

| 既存リソース | 場所 | 用途 |
|-------------|------|------|
| `SciFiCard` | `components/ui/SciFiCard.tsx` | コンパクトカードのラッパー |
| `SciFiProgress` | `components/ui/SciFiProgress.tsx` | 詳細モーダルのスペックバー |
| `HoldSciFiButton` | `components/ui/HoldSciFiButton.tsx` | 詳細モーダルの購入ボタン |
| `SciFiPanel` | `components/ui/SciFiPanel.tsx` | モーダルコンテナ |
| `SciFiHeading` | `components/ui/SciFiHeading.tsx` | モーダルタイトル |
| `getRankColor`, `getRank`, `getWeaponRank` | `utils/rankUtils.ts` | ランク算出・色付け |
| `getOptimalRangeLabel`, `getDecayRateRank` | `utils/rankUtils.ts` | 武器詳細表示 |
| `STATUS_LABELS`, `WEAPON_LABELS` | `utils/displayUtils.ts` | ラベル文字列 |
| `useShopListings`, `useWeaponListings` | `services/api.ts` | アイテム一覧取得 |
| `usePilot` | `services/api.ts` | クレジット取得 |
| `purchaseMobileSuit`, `purchaseWeapon` | `services/api.ts` | 購入API呼び出し |

---

## 6. 既存コードへの影響範囲

| ファイル | 変更内容 | 影響度 |
|---------|---------|--------|
| `app/shop/page.tsx` | レイアウト刷新・コンポーネント分割 | 大 |
| `components/ui/SciFiProgress.tsx` | 変更なし（流用） | なし |
| `components/ui/HoldSciFiButton.tsx` | 変更なし（流用） | なし |
| `components/ui/SciFiCard.tsx` | 変更なし（流用） | なし |
| `utils/rankUtils.ts` | 変更なし（流用） | なし |
| `types/shop.ts` | 変更なし | なし |
| `services/shop.ts` | 変更なし | なし |

新規ファイルは `app/shop/_components/` 以下に追加。`page.tsx` のみ大幅に書き換え。

---

## 7. 実装優先度ロードマップ

### Phase 1 — 情報設計の即時改善（P0）

> 最小変更でユーザーの混乱を即時解消する

- [ ] Sticky クレジットヘッダーの実装（`ShopCreditHeader.tsx`）
- [ ] 「購入可能のみ」フィルターの実装
- [ ] カード内の不足額表示（`(-800 C)` をカード右下に追記）

### Phase 2 — カード & モーダル化（P1）

> Progressive Disclosure によるモバイルUX向上

- [ ] コンパクトカードへの刷新（`MobileSuitCard.tsx` / `WeaponCard.tsx`）
- [ ] 詳細モーダルの実装（`MobileSuitDetailPanel.tsx` / `WeaponDetailPanel.tsx`）
- [ ] スペックバー（`SciFiProgress` 流用）+ ランク色連動

### Phase 3 — PC向け最適化（P2）

> ワイドスクリーンでの一覧・詳細同時表示

- [ ] lg 以上での2カラムレイアウト（カードリスト + 詳細インラインパネル）

### Phase 4 — UX細部（P3）

> 操作の快適性・楽しさの向上

- [ ] 購入後クレジット残高のカウントダウンアニメーション
- [ ] アイテムソート機能（価格昇順/降順、スペック強度順）

---

## 8. 検証方法

1. `npm run dev` でdevサーバーを起動
2. ブラウザのデベロッパーツールでモバイルビュー（375px幅）に切り替え、以下を確認：
   - クレジットヘッダーがスクロール後も固定表示されるか
   - 「購入可能のみ」フィルターで高額アイテムが非表示になるか
   - コンパクトカードタップで詳細モーダルが開くか
   - モーダル最下部の HoldSciFiButton で購入が完了し、クレジットが更新されるか
3. lg幅（1024px以上）で2カラムレイアウトが正しく表示されるか確認

---

## 9. 関連ドキュメント

- [docs/features/parameter-tuning-ui-improvement.md](parameter-tuning-ui-improvement.md) — パラメータチューニングUIの改善事例（設計思想の参考）
- [docs/ui-design/ui-guidelines.md](../ui-design/ui-guidelines.md) — UIデザインガイドライン（モバイルファースト原則）
- [docs/ui-design/sf-ui-components-guide.md](../ui-design/sf-ui-components-guide.md) — SF-UI コンポーネント一覧
