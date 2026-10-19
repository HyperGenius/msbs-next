# SciFiSelect カスタムリストボックス

## 概要

`SciFiSelect`（`frontend/src/components/ui/SciFiSelect.tsx`）を、ブラウザ標準の `<select>` から自作のリストボックスに置き換えた（Issue #667）。
標準 `<select>` は開いたときの選択肢リストがOS/ブラウザ既定のデザインになり、SF風UIから浮いていたため。
戦術設定（ターゲット優先度・交戦距離・武装持ち替えポリシー）では、選択肢ごとの説明文を選択前に比較できるようにした。

## 仕様

- トリガーボタン（現在値＋▼）とポップアップのリストで構成。`variant`（primary / secondary / accent）の配色に対応
- 選択肢に任意の `description` を指定でき、リスト内の項目に小さく併記する
- 下に最大高さ分の空きが無く、上のほうが広い場合は上向きに開く
- 外側クリック・Esc・Tab で閉じる。リストが長い場合は内部スクロール
- 各項目の高さは44px以上（スマホのタップ領域）
- アクセシビリティ: トリガーが `role="combobox"`、リストが `role="listbox"`、項目が `role="option"`。`aria-activedescendant` でキーボード操作中の項目を示す
- キーボード: ↑↓ で移動、Home/End で先頭/末尾、Enter/Space で決定

## API の変更

`onChange` のシグネチャを `ChangeEvent` から値の文字列に変更した。

```tsx
// 変更前
onChange={(e) => setFoo(e.target.value)}
// 変更後
onChange={(value) => setFoo(value)}
```

`value` は `string | number`。`onChange` へは常に文字列で渡るため、数値が必要な呼び出し側は `Number(value)` で変換する。
`name` などネイティブ `<select>` の属性は受け付けない（フォーム送信には使っていない）。

## 利用箇所

- `app/garage/components/TacticsSelector.tsx`（戦術設定。3項目すべてに `description` を設定）
- `app/garage/components/WeaponEquipPanel.tsx`（装備先の機体・スロット）
- `app/garage/components/WeaponInventoryList.tsx`（属性フィルタ）

素の `<select>` は `app/team/page.tsx` と `components/Social/TeamFormationModal.tsx` に残っている。置き換えは後続対応。

## テスト

`SciFiSelect.stories.tsx` の play 関数で、マウス選択・キーボード操作・disabled を検証している（`npx vitest run --project storybook`）。
