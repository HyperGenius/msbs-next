# ルートレイアウトのボトムナビ分スペーシング修正

**バージョン**: 1.2.0
**作成日**: 2026-08-02
**最終更新**: 2026-08-02
**ステータス**: 実装済み（Issue #409）
**対象ファイル**: `frontend/src/app/layout.tsx`, 各`src/app/**/page.tsx`（`min-h-screen`を使用する全ページ）

---

## 1. 概要と目的

モバイル表示（`md`ブレークポイント未満）で、スクロール可能なコンテンツの末尾が`BottomNav`（`fixed bottom-0`、高さ`h-16`=64px）の裏に隠れて表示されない不具合を修正した。

原因は、ルートレイアウトの`main`要素がスクロール領域の下端に`BottomNav`の高さ分の余白を確保していなかったこと。`BottomNav`は`fixed`配置のため通常のドキュメントフローから外れており、`main`側で明示的にスペースを空けない限りコンテンツと重なる。

## 2. 変更内容

### 初回実装（v1.0.0）と回帰

当初は`main`要素（`overflow-y-auto`が設定されたスクロールコンテナ本体）に`pb-16 md:pb-0`を直接追加した。しかしこの実装には回帰バグがあった。`overflow-y-auto`要素の`padding-bottom`は`box-sizing`に関わらず常に`scrollHeight`に加算されるため、子要素（`children`）の実コンテンツがどれだけ短くても`scrollHeight`が`clientHeight`より64px分だけ必ず大きくなり、コンテンツが画面に収まっているページでも縦方向にスクロールできてしまっていた。

### 修正実装（v1.1.0）

`main`自体へのpaddingをやめ、`body`の`flex flex-col`レイアウト内で`main`と`BottomNav`の間に高さ`h-16`（モバイルのみ、`md:hidden`）のスペーサー要素を兄弟として追加した。

```tsx
<main className="flex-1 overflow-y-auto md:overflow-visible">
  {children}
</main>
{/* BottomNavはfixed配置のためflowから外れる。mainの高さをその分だけ事前に縮めておくためのスペーサー */}
<div className="h-16 shrink-0 md:hidden" aria-hidden="true" />
<BottomNav />
```

`main`は`flex-1`のため、フレックスコンテナ内の残り空間（ビューポート高さ − Header高さ − スペーサー64px）にちょうど収まる高さで確保される。これにより：

- コンテンツが短い場合: `main`の`clientHeight`自体が最初からBottomNav分を除いた高さになっているため、`scrollHeight`が`clientHeight`を超えず、不要なスクロールは発生しない
- コンテンツが長い場合: 最後までスクロールしてもBottomNavの裏にコンテンツが隠れない（Issue #409の本来の目的を維持）

### 追加の回帰（v1.2.0）: ページ側の`min-h-screen`によるコンテンツ無しスクロール

v1.1.0でレイアウト側の実装は正しくなったが、Garageページ等で「コンテンツが無い/短いのにY方向にスクロールできる」不具合が別途見つかった。

原因は`layout.tsx`とは別の場所にあった。ほぼ全てのページコンポーネント（`page.tsx`）が、自身のルート要素に`min-h-screen`（`min-height: 100vh`）を指定していた。これらは`layout.tsx`の`<main>`（`flex-1 overflow-y-auto`、高さは`body`のflexレイアウトによりビューポート−Header−BottomNavスペーサー分に確定している）の**内側にネストされた**要素であるにもかかわらず、`min-h-screen`によって「常にビューポート全体以上の高さ」を強制していた。

その結果、ページの実コンテンツがどれだけ短くても、内側要素の高さが外側`<main>`の`clientHeight`を必ず上回り、余白だけの部分までスクロールできてしまっていた。加えて、`layout.tsx`側に既に`<main>`があるため、ページ側でも`<main>`タグを使っている箇所は`<main>`が二重にネストされる状態（landmarkの重複）にもなっていた。

対応として、以下の10ファイルのページルート要素を修正した。

- `src/app/page.tsx`
- `src/app/sign-up/[[...sign-up]]/page.tsx`
- `src/app/sign-in/[[...sign-in]]/page.tsx`
- `src/app/shop/page.tsx`
- `src/app/rankings/page.tsx`
- `src/app/team/page.tsx`
- `src/app/history/page.tsx`
- `src/app/pilot/page.tsx`
- `src/app/garage/page.tsx`
- `src/app/onboarding/page.tsx`

変更内容:
- `min-h-screen` → `min-h-full`（親要素である`layout.tsx`の`<main>`の実高さを最小値とし、ビューポート全体を強制しないようにする）
- ルート要素が`<main>`タグだった箇所は`<div>`に変更（`layout.tsx`側の`<main>`とのネスト重複を解消）

## 3. 既知の制約

- モーダル（`SciFiModal`など）は元々`z-[60]`で`BottomNav`より前面に表示する設計のため、本修正の影響を受けない（`frontend/CLAUDE.md`「よくあるハマりポイント」参照）
- 実機・実ブラウザでのスクロール挙動（コンテンツが無い/短い/長いの3パターン）の目視確認は、Clerkログインが必要なページを含めて別途手動で行う想定（`tsc`のみで型面は確認済み）
