# バトルログ仕様書

## 概要

バトルヒストリー詳細モーダルに表示されるバトルログの仕様を定義する。  
本番環境向けのフィルタリング・抽象化処理、自機フォーカス表示、開発用デバッグログの制御について記述する。

---

## コンポーネント構成

```
BattleDetailModal
├── BattleViewer           # 3D リプレイビューア
├── TurnController         # タイムライン操作
└── BattleLogViewer        # ログ一覧表示
```

### 関連ファイル

| ファイル | 役割 |
|---------|------|
| `frontend/src/components/history/BattleDetailModal.tsx` | モーダル本体・状態管理 |
| `frontend/src/components/history/BattleLogViewer.tsx` | ログ一覧の表示コンポーネント |
| `frontend/src/utils/logFormatter.ts` | ログのフォーマット・フィルタリングユーティリティ |
| `frontend/src/hooks/useBattleLogic.ts` | ログフィルタリングロジックのカスタムフック |

---

## 環境フラグ

| フラグ | 型 | 説明 |
|-------|-----|------|
| `IS_PRODUCTION` | `boolean` | `process.env.NODE_ENV === "production"` で決定 |
| `isProductionPreview` | `boolean` | 開発環境から本番表示をプレビューするトグル（開発環境専用） |
| `isFiltered` | `boolean` | 自機フォーカスフィルタのトグル状態。本番環境では `IS_PRODUCTION` で初期化 |

---

## フィルタリング仕様

### 1. 開発用デバッグログの非表示（本番環境）

本番環境（`IS_PRODUCTION === true`）または本番プレビューモード（`isProductionPreview === true`）では、
以下のパターンに一致するメッセージを含むログを非表示にする。

| パターン | 例 |
|--------|-----|
| `ファジィ推論` | `GelgoogはファジィでZaku IIを最優先ターゲットに決定（優先度スコア: 0.868）` |
| `優先度スコア` | 同上 |
| `UNKNOWN機` | `UNKNOWN機が中距離にDom (NPC)を発見！（索敵確率 82%）` |
| `[FUZZY]` | デバッグプレフィックス付きメッセージ |

**実装箇所:** `logFormatter.ts` の `isProductionDebugLog()` と `useBattleLogic.ts` の `filterRelevantLogs`

```typescript
// logFormatter.ts
const PRODUCTION_DEBUG_PATTERNS: RegExp[] = [
  /ファジィ推論/,
  /優先度スコア/,
  /UNKNOWN機/,
  /\[FUZZY\]/,
];

export function isProductionDebugLog(message: string): boolean {
  return PRODUCTION_DEBUG_PATTERNS.some((pattern) => pattern.test(message));
}
```

---

### 2. 自機フォーカスフィルタ

本番環境では自機（`playerId`）または自機チーム（`playerTeamIds`）に関連するログのみ表示する。

| 優先度 | 対象 | 表示条件 |
|-------|------|---------|
| 最高 | 自機の行動 | `actor_id === playerId`（常に表示） |
| 高 | 自機チームの行動 | `playerTeamIds.has(actor_id)` |
| 高 | 自機へのダメージ・攻撃 | `target_id === playerId`（常に表示） |
| 低 | 上記以外の敵MS行動 | 非表示 |

**実装箇所:** `useBattleLogic.ts` の `filterRelevantLogs`

フィルタの適用条件:
- 本番環境 (`isProduction === true`): 常に自機フォーカスフィルタとデバッグログ除外を適用
- 開発環境の手動フィルタ (`isFiltered === true`): 自機フォーカスフィルタのみ適用
- 開発環境・フィルタ OFF (`isFiltered === false`): すべてのログを表示

---

### 3. メッセージの抽象化（本番環境）

本番環境では以下のメッセージ変換を行い、ゲームリアリティを損なう数値情報を隠蔽する。

| 変換対象 | 変換前 | 変換後 |
|---------|--------|--------|
| 距離 (m) | `450m` | `遠距離` / `中距離` / `近距離` |
| 命中率 | `(命中: 72%)` | 削除 |
| ダメージ数値 | `250ダメージ` | `致命的なダメージ` 等 |

距離の閾値:
- ≤ 200m（200m を含む） → `近距離`
- 200m 超 かつ ≤ 400m（400m を含む） → `中距離`
- 400m 超 → `遠距離`

ダメージの閾値（`target_max_hp` が指定された場合は HP 割合ベース）:
- ≥ 20% HP → `致命的なダメージ`
- ≥ 10% HP → `手痛いダメージ`
- ≥  5% HP → `ダメージ`
- <  5% HP → `軽微なダメージ`

**実装箇所:** `logFormatter.ts` の `formatBattleLog()`

---

## 開発環境の機能

本番環境では非表示になる開発者向けコントロールを提供する。

### フィルタートグル

`BattleLogViewer` 内に表示される2つのボタン（`IS_PRODUCTION === false` のときのみ表示）:

| ボタン | 機能 |
|-------|------|
| 自機関連のみ表示中 / ログフィルター: OFF | 自機フォーカスフィルタのトグル |
| 本番プレビュー中 / 本番プレビュー: OFF | 本番環境の表示を開発中にプレビュー |

`isProductionPreview` が `true` の場合、`useBattleLogic` に `isProduction: true` が渡され、
本番環境と同等のフィルタリングが適用される。

---

## フック: `useBattleLogic`

```typescript
export function useBattleLogic(
  selectedBattle: BattleResult | null,
  mobileSuits: MobileSuit[] | undefined,
  isFiltered: boolean,
  isProduction: boolean = false
)
```

### 返り値

| 値 | 型 | 説明 |
|----|-----|------|
| `ownedMobileSuitIds` | `Set<string>` | プレイヤーが所有する機体 ID セット |
| `playerTeamIds` | `Set<string>` | 自機・僚機の ID セット |
| `playerId` | `string \| null` | 自機 ID |
| `filterRelevantLogs` | `(logs: BattleLog[]) => BattleLog[]` | ログフィルタリング関数 |

---

## ユーティリティ: `logFormatter.ts`

### `isProductionDebugLog(message: string): boolean`

メッセージが本番環境で非表示にすべきデバッグログかどうかを判定する。

### `formatBattleLog(log, isProduction, playerId): DisplayLog`

単一の `BattleLog` を `DisplayLog` に変換する。本番モード時はメッセージを抽象化する。

### `formatBattleLogs(logs, isProduction, playerId): DisplayLog[]`

`BattleLog[]` を `DisplayLog[]` に変換する。本番モード時はデバッグログ除外と自機フォーカスフィルタを適用する。
