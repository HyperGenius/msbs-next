# トップ画面のブート画面（SYSTEM BOOTING）

**バージョン**: 1.0.0
**作成日**: 2026-10-19
**最終更新**: 2026-10-19
**ステータス**: 実装済み（Issue #672）
**対象ファイル**: `frontend/src/app/page.tsx`, `frontend/src/components/Dashboard/SystemBootScreen.tsx`

---

## 1. 概要と目的

トップ画面（`/`）では、バックエンドのコンテナがコールドスタートしている間、「SYSTEM BOOTING」の起動演出（`SystemBootScreen`）を表示する。応答を待つ時間を演出でごまかすための画面であり、バックエンドが応答できる状態ならすぐにダッシュボードを表示する。

Issue #672 以前は、トップ画面に戻るたびにブート画面が表示されていた。

## 2. 表示条件

`page.tsx` の `isSystemBooting` が true の間、ブート画面を表示する。

```ts
const isSystemBooting =
  !isLoaded ||
  (missionsLoading &&
    mobileSuitsLoading &&
    entryStatusLoading &&
    pilotLoading &&
    battlesLoading);
```

- **Clerk の初期化が終わっていない**（`!isLoaded`）、または
- **バックエンドからまだ1つも応答が来ていない**（5つの SWR フックがすべてロード中）

コールドスタート中はすべての API が同時に待たされるため、どれか1つでも応答があればバックエンドは起動済みとみなす。残りのデータはダッシュボードの各セクション側で待つ（例: エントリー状況は「エントリー状況を確認中...」を表示する）。

SWR の `isLoading` は「キャッシュにデータがなく、取得中」のときだけ true になる。取得済みデータがある状態でトップ画面に戻った場合は、再検証中でも `isLoading` は false のため、ブート画面は出ない。

### Issue #672 以前の条件

以前は5つのフックのうち**どれか1つでも**ロード中ならブート画面を出していた（`||` で連結）。そのため最も遅い API にダッシュボード全体が引きずられ、トップ画面に戻るたびにブート画面が表示されていた。

## 3. 表示までの猶予

`SystemBootScreen` は、マウントから `BOOT_SCREEN_DELAY_MS`（400ms）が経つまで、背景色だけの空の要素を描画する。この間に応答が揃えば、ブート画面を一度も出さずにダッシュボードへ切り替わる。応答が速いときに演出が一瞬だけ表示されてチラつくのを防ぐため。

猶予を過ぎると起動演出を始める（350ms ごとにログを1行ずつ表示し、プログレスバーを進める）。演出は応答を待たせない。応答が揃った時点で、演出の途中でもダッシュボードに切り替わる。

## 4. レイアウト

ルート要素は `<div className="min-h-full ...">` にしている。`layout.tsx` 側に `<main>` があるため、ページ側で `<main>` や `min-h-screen` を使わない（`frontend/CLAUDE.md`「ルートレイアウトとページルート要素の規約」、`docs/features/layout-bottomnav-spacing.md`）。Issue #672 以前は `<main className="min-h-screen ...">` で、この規約を守っていなかった。
