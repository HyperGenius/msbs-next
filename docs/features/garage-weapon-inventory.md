# Garage 所持武器一覧（装備先MS表示）

## 概要

Garageページに、プレイヤーが所持する全武器インスタンス（`player_weapons`）を横断的に一覧できる「所持武器一覧」タブを追加した。
機体を1体ずつ選んで装備モーダルを開かなくても、所持している武器の総数・種別・装備状況（どのMSのどのスロットに装備中か、または未装備か）を一目で把握できる。

既存のバックエンドAPI（`GET /api/player-weapons`）・データモデル（`PlayerWeapon`）を変更せずに実現しており、本Issueはフロントエンドの表示層追加が中心（Issue #403）。

---

## UI構成

Garageページ（`frontend/src/app/garage/page.tsx`）にタブ切り替えを追加:

| タブ | 内容 |
|------|------|
| 機体一覧 | 既存の `MobileSuitList`（所持MSのグリッド表示） |
| 所持武器一覧 | 新規追加。所持する全 `PlayerWeapon` インスタンスの一覧 |

### 所持武器一覧（`WeaponInventoryList.tsx`）

各行に以下を表示する:

- 武器名・属性（BEAM/PHYSICAL）・威力/射程/命中ランク（`base_snapshot` から算出）。ランクはS〜Eごとに背景色付きバッジで色分け表示する（`RANK_BADGE_CLASSES`。S=緑, A=青, B=黄, C=橙, D=赤, E=暗赤）
- 装備状態: 装備中なら装備先MS名 + スロット番号、未装備なら「未装備」
  - `equipped_ms_id` が所持MS一覧に見つからない場合は「不明な機体」と表示し、エラーにしない
- 同一マスター武器を複数所持している場合も、`PlayerWeapon.id` 単位で個別の行として表示される

### フィルタ・並び替え

使用頻度で優先度をつけ、1行に複数のUIパターンを混在させないよう配置している:

- 常時表示（高頻度）: 「未装備のみ表示」トグル（漏斗アイコン）、属性フィルタ（すべて / BEAM / PHYSICAL、着弾点アイコン + `SciFiSelect`）
- アイコン + ポップアップメニュー（低頻度）: 並び替え（新しい順 / 古い順 / 装備中が上）は上下矢印アイコンのみのボタンにまとめ、タップ時にメニューを開く方式にして常時表示領域を圧迫しないようにした
- 見出し横に `件数 / 全件数` を表示し、フィルタ適用中であることが分かるようにしている。フィルタで0件になった場合は「フィルタをリセット」ボタンを表示する

属性フィルタ・並び替えはクライアント側でのフィルタリング/ソートだが、「未装備のみ表示」だけは `WeaponInventoryList` 内で `usePlayerWeapons(true)` を呼び直し、`GET /api/player-weapons?unequipped=true` のサーバー側フィルタを使う（`usePlayerWeapons(false)` と同一URLはSWRのグローバルキャッシュで重複排除されるため、OFF時は他画面の全件フェッチと共有される）。所持数が多いユーザーで、装備済み分を毎回無駄に取得しないための対応。
アイコン（`FilterIcon` / `TypeIcon` / `SortIcon` / `EmptyBoxIcon`、`WeaponInventoryList.tsx` 内にインラインSVGで定義）でラベルを短縮している。プロジェクトにアイコンライブラリの導入がないため、依存追加を避けて `currentColor` ベースの最小限のSVGを直接実装した。

### 一覧からの操作

- **カード本体のクリック（すべての行が対象）**: 武器改造モーダル（`WeaponUpgradeModal`）を開く（Issue #413）。装備中・未装備どちらの武器も改造可能
- **装備中の武器の行**: 装備先MS名・スロット番号を含む一体化ボタン「→ {MS名}へ移動（スロットN）」を、カード幅いっぱいの独自ボタン（`SciFiButton` は使わず素の `<button>`）として設置し、押すと装備先MSの `CustomizationModal` を開く（`useGarageEditor.handleNavigateToEquippedMs`）。カードの主目的アクションであるため、下線リンクではなくボタンとして視覚的な重みを持たせている。配色は新色を追加せず既存パレットの範囲内（`#00ff41`）に収め、通常時は1pxボーダー+透明背景、hover/active時のみ緑背景+黒文字に反転する構成にして、常時は主張しすぎない見た目にしている。武器変更モーダルへは自動遷移させず、ユーザーが次のアクション（LOADOUTタブ操作など）を自分で選べるようにする
- **未装備の武器の行** → 装備先MS・スロットをインラインの `SciFiSelect` で選択し、「装備する」ボタンで直接装備できる（`useGarageEditor.handleEquipFromInventory` が `PUT /api/mobile_suits/{ms_id}/equip` を呼び出す既存の `equipWeapon` サービス関数を利用）
- 上記2つの操作（移動ボタン・装備先選択+装備ボタン）はカード本体クリックとは別のアクションのため、内側を `onClick={(e) => e.stopPropagation()}` でラップし、カードの改造モーダルが誤って開かないようにしている

### 武器改造モーダル（`WeaponUpgradeModal.tsx`、Issue #413）

`SciFiModal`（共通モーダルシェル、`z-[60]` で BottomNav の上に重なる）をベースに、`power_bonus` / `accuracy_bonus` それぞれのカードを表示する:

- モーダルを開くと `GET /api/player-weapons/{pw_id}/upgrade-preview/{stat_type}` を2ステータス分並列で呼び出し、次の1ステップのコスト・改造後の値・上限到達フラグを取得する（クライアント側でコスト計算式を複製せず、常にバックエンドを正とする）
- 改造ボタン（`HoldSciFiButton` の長押し確定、既存のMS強化・スキル開発UIと同じ誤タップ防止パターン）を押すと `POST /api/player-weapons/{pw_id}/upgrade`（`steps: 1`）を実行し、成功したら再度プレビューを取得し直して表示を更新する
- 改造後の値からランク（`getWeaponRank("weapon_power" | "weapon_accuracy", value)`）を計算し、ランクアップする場合は現在ランクの代わりに改造後ランクを表示して「✨UP!」を添える
- 上限到達時（`at_max_cap: true`）はボタンの代わりに「上限に達しています」の非活性表示にする
- 改造成功時は `onUpgraded(response.player_weapon)` で呼び出し元（`WeaponInventoryList`）に更新後の `PlayerWeapon` を渡し、一覧側の `resolveSpec`（`base_snapshot + custom_stats` をマージして実効スペックを計算、Issue #413 で改造差分を反映するよう修正）がランクバッジに即座に反映する。同時に `usePlayerWeapons` のSWRキャッシュとパイロットのクレジット残高（`usePilot`）も再検証する（`useGarageEditor.handleWeaponUpgraded`）

### 空状態・少数件時のレイアウト

- 0件（未所持、またはフィルタで該当なし）の場合は、アイコン付きの空状態メッセージ（所持数ゼロなら購入導線への案内文、フィルタ起因ならリセットボタン）を表示し、単なる空白に見えないようにしている
- パネル自体には最小高さを設けていないため、1件のみの場合でもカード分の高さしか占有しない。ページ全体の縦方向の余白（`min-h-screen` の main 要素に対してコンテンツが少ない場合に生じる下部の余白）は本コンポーネント単体では解消しておらず、Garageページ全体のレイアウト方針として別途検討が必要

---

## 関連ファイル

- `frontend/src/app/garage/page.tsx` — タブ切り替えUIの追加。`pilot` / `handleWeaponUpgraded` を `WeaponInventoryList` に渡す
- `frontend/src/app/garage/hooks/useGarageEditor.ts` — `activeTab` 状態、`handleNavigateToEquippedMs` / `handleEquipFromInventory` / `handleWeaponUpgraded`（Issue #413）ハンドラを追加
- `frontend/src/app/garage/components/WeaponInventoryList.tsx` — 所持武器一覧コンポーネント。自身で `usePlayerWeapons()` を呼び出し、装備先MSの参照は `mobileSuits` から作った `Map<id, MobileSuit>`（`msById`）でO(1)解決する。`resolveSpec` は `base_snapshot + custom_stats` をマージした実効スペックを返す（Issue #413）。カードクリックで `WeaponUpgradeModal` を開く
- `frontend/src/app/garage/components/WeaponUpgradeModal.tsx` — 武器改造モーダル（新規、Issue #413）
- `frontend/src/hooks/usePlayerWeapons.ts` — 所持武器取得フック（既存、変更なし。`unequippedOnly` 引数で `?unequipped=true` を切り替え可能）
- `frontend/src/app/garage/constants.ts` — `getWeaponSlots()`（既存、スロット選択に再利用）
- `frontend/src/services/weaponEngineering.ts` / `frontend/src/types/shop.ts` — 武器改造APIクライアント・型（Issue #411 で実装済み、本Issueで初めて画面から利用）
- `backend/app/routers/player_weapons.py` / `backend/app/services/weapon_service.py` / `backend/app/services/weapon_engineering_service.py` — 武器改造API・ロジック（既存、変更なし）

---

## 今後の拡張

- 一覧から武器の売却・破棄（`DELETE /api/player-weapons/{pw_id}`）を行う導線は未実装（別Issueで検討）

---

## テスト

- `cd frontend && ./node_modules/.bin/tsc --noEmit` — 型チェック
- `cd frontend && npx vitest run tests/unit/` — 既存ユニットテスト（本機能はSWRフック・Reactコンポーネントが中心で、`frontend/CLAUDE.md` の方針によりユニットテスト対象外）
- `cd frontend && npm run build` — 本番ビルド確認
