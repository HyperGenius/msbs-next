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

---

## バックエンド: `GET /api/battles/{battle_id}/logs`（遅延ロード配信）

バトルログは `battle_results` とは別テーブル `battle_logs`（`BattleLogRecord`, `backend/app/models/models.py`）に
バトルセッション単位で1レコード保存されており、`GET /api/battles/{battle_id}/logs` がリプレイ表示時にのみ
`battle_results.battle_log_id` 経由で遅延ロードする（一覧表示の `GET /api/battles` には含まれない）。

### レスポンス生成はDBの検証済みdictをそのまま返す（Pydanticオブジェクト化しない）

`backend/main.py` の `get_battle_logs` は、DBから取得した `list[dict]` を `BattleLog(**entry)` で
Pydanticオブジェクト化しない。保存時点で `strip_debug_fields`（`app/engine/battle_utils.py`）により
既にBattleLog相当のJSON互換dictとして確定しているため、配信時に再度オブジェクト化・再バリデーション
する意味がない。

`room_size=50/100` 規模のバトルはログが10万件を超えることがあり、
「DBのdict → `BattleLog`オブジェクト → `response_model`再バリデーション → JSON」という
従来の経路ではオブジェクト生成のオーバーヘッドでCloud Run（メモリ上限1GiB）がOOMする
不具合が実際に発生した（Issue #486）。本番の実データ（110,648件のログ、TOAST圧縮後12.67MB）で
比較した結果、オブジェクト化を挟む従来経路はレスポンス生成だけで約560MBの追加メモリを要したのに対し、
dictを直接返す経路は約66MBで済んだ（実測、`resource.getrusage().ru_maxrss` ベース）。

新たにこのエンドポイントのレスポンス生成ロジックを変更する場合、`BattleLog(**entry)` のような
オブジェクト化を経由するdiffは大規模バトルでのメモリ悪化に直結するため避けること。

### レスポンスはNDJSONでチャンク送出する（バックエンド・フロント双方）

`get_battle_logs` は `list[dict]` を1個のJSON文字列に組み立てて `JSONResponse` で返すのではなく、
`_ndjson_lines()`（`main.py`）が1エントリずつ `json.dumps` してyieldする `StreamingResponse`
（`media_type="application/x-ndjson"`, 1行1エントリのJSON）で返す（Issue #488）。前段の
「dictを直接返す」対応（Issue #486）でオブジェクト化のコストは解消したが、`JSONResponse` は
それでもレスポンス全体を1個の巨大な文字列としてメモリに組み立ててから返すため、その文字列自体の
サイズがバトル規模にそのまま比例する構造は残っていた。NDJSONで1行ずつ送出することで、ASGIサーバーが
送出済みのチャンクを解放でき、ピークメモリをレスポンス全体のサイズに比例させずに済む。

フロントエンド側（`frontend/src/services/battle.ts` の `fetchBattleLogsNdjson`）も
`res.json()` で全量を一括バッファする実装から、`res.body.getReader()` + `TextDecoder` による
行単位の逐次パースに変更した。**バックエンドだけをストリーミング化してもフロントが `res.json()` の
ままではフロント側のピークメモリは変わらない**ため、必ずセットで扱うこと（#486の議論で判明した
落とし穴）。`res.body` が使えない環境（テスト用のResponseモック等）向けに `res.text()` への
フォールバックも用意している。

### GZip圧縮

`main.py` に `GZipMiddleware`（`minimum_size=1000`）を追加済み。StreamingResponseに対しても
チャンクごとに圧縮される。110,648件のレスポンスは86MB→約4.9MBまで圧縮される（転送量対策であり、
上記メモリ問題そのものの対策ではない）。

### `battle_logs.logs` のDB列型はPostgreSQLでは `JSONB`（Issue #489）

`BattleLogRecord.logs`（`backend/app/models/models.py`）の `sa_column` は
`Column(JSON().with_variant(JSONB, "postgresql"))` として定義している。PostgreSQL接続時のみ
`JSONB`（バイナリ格納）として扱われ、テストで使うSQLiteなど`JSONB`を持たない方言では
従来通り `JSON` として扱われる（`with_variant` は方言ごとに実際の型を切り替える仕組みで、
テストDB構成を変えずに済む）。マイグレーション
（`alembic/versions/a5b6c7d8e9f0_migrate_battle_logs_logs_to_jsonb.py`）は
`ALTER COLUMN logs TYPE JSONB USING logs::JSONB` をPostgreSQL接続時のみ実行する。
`JSONB` はキー順序を保証しないが、バトルログはキー順序に依存した処理をしていないため
問題ない。

GINインデックス（`USING GIN (logs)`）はIssue #489の本文で「任意」とされていたが、Neon実DBで
試作したところインデックスサイズが約20MBとテーブル本体とほぼ同じになった（ログ内の
全キー・全階層をインデックス化するため）。ストレージ削減が目的の一つである本Issueでは
作成を見送った。将来actor/action_type等の具体的な検索要件が固まった時点で、部分インデックス
（特定キーのみを対象にする等）を含めて別途検討すること。

### 巨大行（数十MB級）はALTER COLUMN TYPE実行前に退避・削除する

`ALTER TABLE ... ALTER COLUMN ... TYPE` はテーブル全体を書き換える単一トランザクション・
ACCESS EXCLUSIVEロックの操作であり、バッチ分割ができない。Neonの実データには1行で
テキスト換算約86MB（`pg_column_size`約12.67MB）に達するログが複数件存在し、これを含んだ
まま `logs::JSONB` キャストを実行すると、`maintenance_work_mem` を64MB→512MBへ引き上げても
`OutOfMemory` になった（Neonのコンピュートサイズ自体が小さいことが原因）。そのため
マイグレーション内の `_archive_and_delete_oversized_battle_logs()` が `pg_column_size(logs)`
が2MBを超える行を、生JSONテキストのまま
`backend/scripts/verify/output/battle_logs_jsonb_migration_backup/`（`.gitignore`対象）へ
バックアップした上で削除してから、残りの行に対してキャストを実行する。`battle_results`
側は集計値が既に非正規化カラムとして保存済みのため、削除対象行を参照する
`battle_results.battle_log_id` をNULLに更新するだけで一覧表示への影響はない
（詳細はマイグレーションファイル自体のdocstringを参照）。
