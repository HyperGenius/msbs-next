# アバター/ボトムナビ UI統一

**バージョン**: 1.0.0
**作成日**: 2026-08-02
**最終更新**: 2026-08-02
**ステータス**: 実装済み（Issue #406）
**対象ファイル**: `frontend/src/components/Header.tsx`, `frontend/src/components/Avatar.tsx`, `frontend/src/components/BottomNav.tsx`, `frontend/src/components/icons/TablerIcons.tsx`

---

## 1. 概要と目的

ヘッダーのアバター表示とボトムナビゲーションの見た目に一貫性がなかった問題を解消する。

- アバターはClerkの`UserButton`に依存しており、画像未設定時はClerk側のデフォルト生成アバター（グラデーション背景のイニシャル画像）がそのまま表示されていた
- ボトムナビはアイコンが絵文字で、アクティブ項目（Garage）のみ視覚的な強調ルールが他と揃っておらず中途半端に見えていた

これらを「装飾」ではなく「ステータス表示の一部」として、緑モノクロ基調のルールに統一した。

## 2. 変更内容

### 2.1 共有アイコンセット（`frontend/src/components/icons/TablerIcons.tsx`）

[Tabler Icons](https://tabler.io/icons)（outline, MIT License）のSVGパスをローカルに複製し、`IconHome` / `IconTool` / `IconShoppingCart` / `IconHistory` / `IconUsers` / `IconUser` / `IconMenu2` として集約。Header・BottomNavなど複数コンポーネントで共有するグローバルアイコンは、以後このファイルに追記して同一セットのみを使う（`frontend/CLAUDE.md`「アイコンの扱い」参照）。

### 2.2 アバター（`Avatar.tsx`）

- `UserButton`の`appearance`で`avatarBox`を線幅1pxの緑アウトライン円（`border border-[#00ff41] bg-transparent`）に変更
- `useUser()`の`hasImage`フラグでユーザーが独自の画像をアップロード済みかを判定
  - 未設定時: Clerkのデフォルト生成アバター（`avatarImage`）を`opacity-0`で非表示にし、代わりに`IconUser`（緑モノクロ）を`pointer-events-none`でオーバーレイ表示
  - 設定済み時: そのままユーザーの画像を表示
- グラデーションは一切使用しない

### 2.3 ボトムナビ（`BottomNav.tsx`）

- アイコンを絵文字からTabler outlineアイコンに統一
- 「アクティブ=塗り、非アクティブ=線画」の強弱ルールを廃止し、全項目を線画（outline）で統一
- アクティブ状態は「文字色を明るい緑（`text-[#00ff41]`）にする＋下線インジケータ（`border-b-2 border-[#00ff41]`）」のみで表現。非アクティブは`text-[#00ff41]/40`＋透明ボーダー（レイアウトシフト防止）
- ラベルの有無・フォントサイズは変更前と同一

## 3. 既知の制約

- Clerkの`UserButton`はメニュー（アカウント管理・サインアウト）機能をそのまま利用しているため、トリガー部分の見た目のみをオーバーレイで差し替えている。Clerk側の内部DOM構造が変わった場合、オーバーレイの位置がずれる可能性がある
- ログイン状態でのアバター表示の目視確認は、リポジトリにClerkテストトークンを使ったE2E環境がないため未実施（`tsc` / `vitest` / 未ログイン時のブラウザ確認のみ）
