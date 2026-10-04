# 機体ランクの閾値

## 概要

機体の HP・装甲・機動性のランク（S〜E）は、どの画面でもバックエンドと同じ閾値で表示する。

Issue #604 で、Garage の機体詳細モーダル（STATUS タブ）のランクが MS一覧と一致しない不具合を修正した。

## 不具合の原因

フロントエンド（`frontend/src/utils/rankUtils.ts`）に閾値表が2種類あり、画面ごとに別の表を使っていた。

| 画面 | 使っていた閾値 | 機動性（S / A / B） |
|---|---|---|
| MS一覧・ダッシュボード・バトル結果 | API の `hp_rank` 等、または `getMobileSuitRanks()`（`backend/data/master/thresholds.json` と同じ値） | 2.0 / 1.5 / 1.2 |
| 詳細モーダル STATUS・ショップの機体カード | `getRank()`（`STAT_CAPS` に対する割合） | 2.7 / 2.4 / 2.1 |

例えば機動性 2.1〜2.39 の機体は、一覧で S、詳細モーダルで B と表示されていた。

## 閾値の扱い

| ステータス | 閾値の基準 |
|---|---|
| HP・装甲・機動性 | `backend/data/master/thresholds.json`（`MOBILE_SUIT_RANK_THRESHOLDS`） |
| 武器の威力・射程・命中率 | `backend/data/master/thresholds.json` |
| 格闘・射撃適性、命中・回避・加速・旋回ボーナス | `STAT_CAPS` に対する割合（バックエンドにランク定義が無いため） |

* `getRank()` と `getMobileSuitRanks()` は、HP・装甲・機動性に同じ `MOBILE_SUIT_RANK_THRESHOLDS` を使う
* `thresholds.json` を変更した場合は、`rankUtils.ts` の値も同時に更新する
* 値がずれていないことを `frontend/tests/unit/rankUtils.test.ts` で `thresholds.json` を読んで確認している

## 強化画面への影響

`thresholds.json` では、機動性 2.0 以上（上限 3.0）と装甲 100 以上（上限 120）がすべて S になる。この範囲で強化してもランクは S のままで、「RANK UP!」も出ない。強化の進み具合は、上限値に対する割合で描く `SciFiBlockIndicator` で示す。

上限付近でもランクを細かく分けたい場合は、`thresholds.json` 自体を見直す。
