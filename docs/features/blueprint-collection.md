# 設計図コレクション（図鑑）画面（`/collection`）

## 概要

Epic #550「戦利品ドロップと設計図システム」の Sub-Issue 7（Issue #566）。
機体・武器の設計図の所持・未所持と収集率を一覧で確認できる。
未所持の設計図には、入手できる戦域を表示する。
次に狙う設計図を決め、「その戦域に出撃する理由」を作ることが目的。
技術タブでは、技術ごとの技術Lv・累計断片数・技術断片の入手先を確認できる（Issue #569）。

API・戦域の表示の変換は `blueprint-system.md` の「設計図コレクション（図鑑）」を参照。

---

## 画面構成

```
┌ BLUEPRINT COLLECTION ─────────── 設計図図鑑 ┐  ← sticky ヘッダー
│ [Mobile Suits] [Weapons] [Tech]               │  ← タブ
│ 収集率                          3 / 8（37%）  │
│ ███████░░░░░░░░░░░░                           │
│                     全体 5 / 12（41%）（標準配備を除く）│
│ [すべて 10] [未所持 5] [所持 3] [標準配備 2]    │  ← 絞り込み（件数付き）
└───────────────────────────────────────────────┘
┌ 設計図カード ┐ ┌ 設計図カード ┐                  ← sm 以上は2列
```

* 要ログイン。`middleware.ts` の公開ルートに含めていないため、Clerk のルート保護の対象
* データは `useBlueprintCollection()`（`src/services/blueprints.ts`、SWR）で `GET /api/blueprints/collection` から取得する
* 技術タブのデータは `useTechnologies()`（`src/services/technologies.ts`、SWR）で `GET /api/technologies/me` から取得する
* ページのルート要素は `min-h-full`（`min-h-screen` は使わない。`frontend/CLAUDE.md`「ルートレイアウトとページルート要素の規約」）

### 収集率

* 分母は標準配備を除いた設計図の数。分子はそのうち所持している数
* ヘッダーの大きい表示は選択中のタブの収集率。下の小さい表示は機体・武器を合わせた全体の収集率
* 割合は切り捨て。100% は全件所持のときだけになる
* 対象が0件なら「対象なし」

### 絞り込みと並び順

* 絞り込み: すべて・未所持・所持・標準配備。ボタンに件数を表示する
* 並び順: 未所持 → 所持 → 標準配備。同じ状態の中は名前順（`localeCompare(…, "ja")`）
* 並べ替え・絞り込み・収集率の計算は `src/utils/blueprintCollection.ts` の純粋関数（`filterAndSortCollection()`・`collectionProgress()`）。テストは `tests/unit/blueprintCollection.test.ts`

---

## 設計図カード（`src/components/collection/BlueprintCollectionCard.tsx`）

1行目に「機体設計図／武器設計図」と機体の勢力、2行目に名前、3行目に状態ごとの補足を出す。右上に状態のバッジを置く。

| 状態 | 条件 | 配色 | 補足 |
|---|---|---|---|
| 所持 | `is_standard_issue = false` かつ `is_owned = true` | シアン（`LootItemCard` の新規入手と同じ系統）。バッジは塗りつぶし | 「入手日 YYYY/M/D」と入手経路（ドロップ／導入時の付与）。技術Lvが足りなければ、その下に「サイコミュ技術 Lv2 が必要（現在 Lv1）」をアンバーで1行ずつ出す（Issue #569） |
| 未所持 | `is_standard_issue = false` かつ `is_owned = false` | 緑の控えめな枠。アイコンを薄く表示 | 入手先（下表） |
| 標準配備 | `is_standard_issue = true` | グレー | 「設計図なしで購入できます」。入手先は出さない |

未所持の補足:

| 条件 | 表示 |
|---|---|
| パイロットの勢力では購入できない機体（`is_available_to_faction = false`） | 「あなたの勢力では入手できません」（赤） |
| 入手できる戦域が無い（`obtainable_theaters` が空） | 「現在は入手できません」 |
| 入手できる戦域がある | 「入手先」の後に戦域をチップで並べる。勝利時のみなら「全戦域（勝利時のみ）」 |

* 標準配備品は、所持記録があっても「標準配備」として表示する
* 勢力の表示: `FEDERATION` は「地球連邦軍」（シアン）、`ZEON` は「ジオン公国軍」（アンバー）
* 長い名前は1行で省略し、`title` 属性で全文を出す
* ドロップ率は表示しない
* 足りない技術Lvは `tech_requirements` のうち `current_lv < required_lv` のもの（`unmetTechRequirements()`、`src/utils/technology.ts`）。文言はショップと同じ `formatMissingTech()`
* ストーリー: `Collection/BlueprintCollectionCard`（所持・所持しているが技術Lvが足りない・導入時の付与・未所持・勝利時のみ・複数の戦域・入手先なし・勢力外・標準配備・長い名前）

---

## 技術タブ（`src/components/collection/TechnologyProgressCard.tsx`、Issue #569）

技術ごとに1枚のカードを技術ID順に並べる。収集率と絞り込みは出さない。

| 表示 | 内容 |
|---|---|
| 名前・Lv | 技術名と「Lv1/3」 |
| 説明 | 技術マスターの `description` |
| 進捗バー | 次のLvまでの進捗。累計数 ÷ 次のLvの閾値（切り捨て、`techProgressPercent()`）。最大Lvなら100% |
| 累計 | 「累計 5 個・次のLvまであと 3 個」。最大Lvなら「最大Lv（以降の断片は +500 C に換金）」 |
| 入手先 | 設計図と同じ戦域のチップ（`obtainable_theaters`）。無ければ「現在は入手できません」 |

* 最大Lvのカードはシアン、それ以外は緑
* ストーリー: `Collection/TechnologyProgressCard`（未入手・途中・最大Lv・勝利時のみ・入手先なし）

---

## 画面への導線

| 場所 | 導線 |
|---|---|
| BottomNav（モバイル）のメニュー | 「Collection」（アイコンは設計図と同じ `IconFileCertificate`） |
| Header（デスクトップ）のナビゲーション | 「Collection」ボタン |
| ショップの詳細パネル（機体・武器） | 未解放のアイテムの「未解放 (LOCKED)」の下に「図鑑で入手先を確認する」（Issue #569 で技術断片も対象にしたため「設計図図鑑」から変更） |

---

## 影響範囲

| ファイル | 変更内容 |
|---|---|
| `backend/app/models/models.py` | `BlueprintCollectionItem`・`ObtainableTheater` を追加 |
| `backend/app/services/blueprint_collection_service.py`（新規） | `BlueprintCollectionService.get_collection()`・`theater_label_for()` |
| `backend/app/routers/blueprints.py` | `GET /api/blueprints/collection` を追加 |
| `frontend/src/types/blueprint.ts`（新規） | 図鑑の型。`types/battle.ts` のバレルに追加 |
| `frontend/src/services/blueprints.ts`（新規） | `useBlueprintCollection()`。`services/api.ts` のバレルに追加 |
| `frontend/src/utils/blueprintCollection.ts`（新規） | 状態・並び順・収集率・入手先の表示の判定 |
| `frontend/src/components/collection/BlueprintCollectionCard.tsx`（新規） | 設計図1件のカードとストーリー |
| `frontend/src/app/collection/page.tsx`（新規） | 図鑑ページ |
| `frontend/src/components/BottomNav.tsx`, `Header.tsx` | 図鑑へのリンク |
| `frontend/src/app/shop/_components/MobileSuitDetailPanel.tsx`, `WeaponDetailPanel.tsx` | 未解放のときの図鑑へのリンク |

---

## 後続の対応

* 戦域ローテーション（Sub-Issue 10）で、`theater_label_for()` を実際の戦域名に対応させる
* 技術断片・技術Lv（Sub-Issue 8）の表示は Issue #569 で追加した（技術タブ・所持済み設計図の足りない技術Lv）
