# バトル結果モーダル（`BattleResultModal`）

## 概要

バトル終了時にホーム画面で表示するリザルト画面。
Issue #564（Epic #550 Sub-Issue 6）で、デザインの見直し、戦利品欄の追加、出撃機体のランク表示の修正、リプレイへの導線の追加を行った。

* コンポーネント: `frontend/src/components/Dashboard/BattleResultModal.tsx`
* ストーリー: `frontend/src/components/Dashboard/BattleResultModal.stories.tsx`
* 呼び出し元: `frontend/src/app/page.tsx`

## 表示の契機

| 経路 | 結果の渡し元 | 戦利品 | リプレイを見る |
|---|---|---|---|
| ソロミッション | `useBattleSimulation.ts`（`POST /api/battle/simulate` の `rewards`） | `rewards.loot` | 出さない（ホーム画面に BattleViewer を直接表示しているため） |
| 未読の定期バトル | `useUnreadBattleQueue.ts`（`GET /api/battles/unread`） | `BattleResult.loot` | 出す |

## 画面構成

上から次の順に並べる。本文だけをスクロールさせ、フッターのボタンは常に画面内に置く（モバイル幅でも CONTINUE までスクロール不要）。

| 領域 | 内容 |
|---|---|
| ヘッダー | `// BATTLE RESULT`、結果タイトル（MISSION COMPLETE / MISSION FAILED / DRAW）、勝利・敗北・引き分け |
| 出撃機体 | 機体名、HP・装甲・機動性のランク、メイン・サブ武器の名前と威力ランク。スナップショットが無ければ出さない |
| 獲得報酬 | 撃墜・EXP・CREDITS の3マス。レベルアップ時は「LEVEL UP Lv.X → Lv.Y」の行を追加する |
| 戦利品 | `LootList`。空配列は「戦利品なし」、`null` は欄ごと出さない。設計図と技術断片（Issue #569）を同じ一覧に表示する |
| フッター | 「リプレイを見る」（未読の定期バトルのみ）、CONTINUE |

### 配色・書体

ホーム画面の Sci-Fi トーン（`font-mono`、`#0a0a0a` の背景、`// 見出し` 形式のセクション見出し）にそろえた。
勝敗ごとの色は、ホーム画面の `BattleResultAnnouncer` と同じ。

| 勝敗 | 色 |
|---|---|
| WIN | `#00ff41`（グリーン） |
| LOSE | `#ffb000`（アンバー） |
| DRAW | `#00f0ff`（シアン） |

* 絵文字（🎉・⚠️）による演出は廃止した
* 長い機体名・武器名・戦利品名は1行で省略し、`title` 属性で全文を表示する
* 撃墜数 0 はグレーで表示する。未ログインのソロミッション（報酬なし）は撃墜のみ表示する
* コメントアウトされていた「撃墜 / 生還」表示は削除した。定期バトルの `ms_snapshot` はエントリー時点（満タンHP）のため、HP から生還を判定できない

## 演出

| 時刻 | 演出 |
|---|---|
| 0.3 秒 | カードを表示 |
| 0.9 秒 | 獲得報酬を表示し、EXP・CREDITS を 1.5 秒でカウントアップ |
| 2.4 秒 | 戦利品を表示。設計図の新規入手と技術Lvの上昇はシアンの光の走査と発光（`globals.css` の `loot-new-*`） |
| 2.4 秒（入手演出ありは 3.4 秒） | レベルアップ時、LEVEL UP のオーバーレイを 2 秒表示して消す |

* 入手演出とレベルアップの演出が重ならないよう、入手演出があるときはレベルアップを遅らせる。入手演出の有無は `isHighlightedLoot()`（`src/utils/technology.ts`）で判定する
* レベルアップのパーティクルは配置を固定値にした。描画中に `Math.random()` を呼ぶと、再描画やストーリーごとに見た目が変わるため
* `animate={false}` を渡すと、段階表示とカウントアップを省いて最終状態を表示する（ストーリーの比較用）
* `prefers-reduced-motion` のときは、戦利品の入手演出を止める

## 出撃機体のランク

Garage の機体一覧と同じランクを表示する。

* バトル結果の `ms_snapshot` は `MobileSuit`（DBテーブル）の `model_dump()` で、`hp_rank` などのランクを含まない。修正前はモーダルが常に `C` を表示していた
* `getMobileSuitRanks()`（`src/utils/rankUtils.ts`）に算出を寄せた。API のランクがあればそれを使い、無ければ `backend/data/master/thresholds.json` と同じ閾値で算出する
  * `getRank()` の HP・装甲・機動性の閾値は `STAT_CAPS` 基準（強化画面用）で、API のランクと値が異なる。そのため機体ランクには使わない
  * `MobileSuitRankBadges`・`EntrySelectionModal`・`enrichMobileSuit()` が `getMobileSuitRanks()` を使う
* 武器の威力ランクは `getWeaponPowerRank()`（`power_rank` が無ければ威力から算出）。Garage の `LoadoutManager` と同じ算出
* 閾値がバックエンドとずれていないことを `tests/unit/rankUtils.test.ts` で `thresholds.json` を読んで確認している

## リプレイへの導線

1. 「リプレイを見る」を押すと、結果モーダルを閉じて `BattleDetailModal`（バトル履歴と同じ）を開く
2. 開いた時点でそのバトルを既読にする（CONTINUE と同じ `POST /api/battles/{id}/read`）
3. リプレイを閉じると、未読キューの次の結果モーダルを表示する

* リプレイを開いている間は `currentUnreadBattle` を空にしない。未読キューはこれが空になるまで次の結果を出さない
* ミッション名は `getMissionName()`（`src/utils/missionName.ts`、バトル履歴と共通）で組み立てる

## Storybook のストーリー

| 分類 | ストーリー |
|---|---|
| 勝敗 | `Win` / `Lose` / `Draw` |
| 戦利品 | `LootNewBlueprint` / `LootConverted` / `LootTechFragmentLevelUp` / `LootEmpty` / `LootLegacyBattle` |
| レベルアップ | `LevelUp` / `LevelUpWithNewLoot` |
| その他の状態 | `ZeroKills` / `NoSnapshot` / `NoRewards` / `LongNames` / `UnreadBattleWithReplay` |
| 画面幅 | `MobileFull` / `MobileLose`（375px）、`DesktopFinalState`（1280px、演出なし） |

戦利品1件の表示は `Loot/LootItemCard`（新規・換金・技術断片の通常の入手・Lvアップ・最大Lv到達・最大Lv後の換金・マスター削除済み・長い名前・一覧の状態・履歴のバッジ）で確認できる。

## 技術断片の表示（Issue #569）

`LootItemCard` は `kind` で設計図と技術断片を出し分ける。技術断片のアイコンは `IconCpu`（`TablerIcons.tsx`）。

| 状態 | 配色 | 説明文（`techFragmentLootMessage()`） | 右端 |
|---|---|---|---|
| 通常の入手 | 緑 | 「累計 5 個・次のLvまであと 3 個」 | `+1` |
| Lvアップ | シアン（入手演出あり） | 「Lv2 に上昇！ 累計 8 個」。最大Lvなら「Lv3（最大） に上昇！」 | `LV UP` |
| 最大Lv後の換金 | アンバー | 「最大Lvのため +500 C に換金」 | `+500 C` |

* 1行目に「技術断片」と「Lv2/3」、2行目に技術名を出す
* 換金したクレジットは、設計図の換金と同じく獲得報酬のクレジットとは分けて表示する
* バトル履歴のバッジ（`LootBadge`）は、設計図の新規入手 → `NEW`、技術Lvの上昇 → `LV UP`、換金 → 換金額の合計、Lvの上がらない技術断片だけ → `+断片` の優先順で1つ出す（`lootBadgeOf()`）
